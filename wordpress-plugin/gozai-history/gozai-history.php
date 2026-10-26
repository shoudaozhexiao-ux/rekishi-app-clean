<?php
/**
 * Plugin Name: ござい歴史アプリ
 * Description: 歴史の60年差比較・今年の予想・ニュースを記事内で表示します。ショートコード: [gozai_history_app]
 * Version: 1.0.1
 * Requires at least: 6.0
 * Requires PHP: 7.4
 * License: GPL-2.0-or-later
 */
if (!defined('ABSPATH')) { exit; }

final class Gozai_History_App {
    const VERSION = '1.0.1';
    const NS = 'gozai-history/v1';

    public static function init() {
        add_action('rest_api_init', array(__CLASS__, 'routes'));
        add_shortcode('gozai_history_app', array(__CLASS__, 'shortcode'));
        add_action('wp_enqueue_scripts', array(__CLASS__, 'enqueue_for_post'));
    }
    public static function enqueue_for_post() {
        global $post;
        if ($post && isset($post->post_content) && has_shortcode($post->post_content, 'gozai_history_app')) { self::enqueue_assets(); }
    }
    private static function enqueue_assets() {
        $base = plugins_url('assets/', __FILE__);
        wp_enqueue_style('gozai-history', $base . 'app.css', array(), self::VERSION);
        wp_enqueue_script('gozai-history-core', $base . 'core.js', array(), self::VERSION, true);
        wp_enqueue_script('gozai-history', $base . 'app.js', array('gozai-history-core'), self::VERSION, true);
    }
    public static function shortcode() {
        self::enqueue_assets();
        $id = wp_unique_id('gozai-history-');
        return '<section id="' . esc_attr($id) . '" class="gh-app" data-rest="' . esc_url(rest_url(self::NS . '/')) . '" aria-label="六十年の連環 歴史アプリ"><p role="status">歴史アプリを読み込んでいます。</p><noscript>このアプリにはJavaScriptが必要です。</noscript></section>';
    }
    public static function routes() {
        register_rest_route(self::NS, '/history', array(
            'methods' => 'GET', 'permission_callback' => '__return_true',
            'callback' => array(__CLASS__, 'history'),
            'args' => array(
                'year' => array('required' => true, 'validate_callback' => array(__CLASS__, 'valid_year')),
                'scope' => array('default' => 'world', 'validate_callback' => array(__CLASS__, 'valid_scope')),
            ),
        ));
        register_rest_route(self::NS, '/news', array(
            'methods' => 'GET', 'permission_callback' => '__return_true',
            'callback' => array(__CLASS__, 'news'),
            'args' => array('q' => array('default' => '人工知能', 'validate_callback' => array(__CLASS__, 'valid_query'))),
        ));
    }
    public static function valid_year($v) {
        if (!is_int($v) && !is_string($v)) { return false; }
        return preg_match('/^[0-9]{4}$/D', (string) $v) && (int) $v >= 1800 && (int) $v <= (int) gmdate('Y');
    }
    public static function valid_scope($v) { return in_array($v, array('japan', 'world'), true); }
    public static function valid_query($v) {
        return is_string($v) && self::length($v) >= 1 && self::length($v) <= 80 && !preg_match('/[\x00-\x1F\x7F]/', $v);
    }
    private static function length($s) { return preg_match_all('/./us', $s, $unused); }
    private static function truncate($s, $n) {
        if (function_exists('mb_substr')) { return mb_substr($s, 0, $n, 'UTF-8'); }
        preg_match_all('/./us', $s, $chars);
        return implode('', array_slice($chars[0], 0, $n));
    }
    private static function error($code, $message, $status = 502) {
        return new WP_Error($code, $message, array('status' => $status));
    }
    private static function budget() {
        // Bound upstream traffic across all anonymous visitors; no visitor identifiers are stored.
        $key = 'gh_budget_' . gmdate('YmdHi');
        $count = (int) get_transient($key);
        if ($count >= 60) { return false; }
        set_transient($key, $count + 1, 90);
        return true;
    }
    private static function cached($key, $ttl, $loader) {
        $fresh = get_transient($key);
        if (is_array($fresh)) { $fresh['stale'] = false; return $fresh; }
        $stale = get_transient($key . '_stale');
        $lock = $key . '_lock';
        if (get_transient($lock)) {
            if (is_array($stale)) { $stale['stale'] = true; return $stale; }
            return self::error('gh_busy', '資料を取得中です。少し待ってから再読み込みしてください。', 503);
        }
        $failure = get_transient($key . '_error');
        if ($failure) {
            if (is_array($stale)) { $stale['stale'] = true; return $stale; }
            if (is_array($failure) && isset($failure['code'], $failure['message'], $failure['status'])) { return self::error($failure['code'], $failure['message'], $failure['status']); }
            return self::error('gh_retry', '外部サービスから取得できません。少し待ってから再試行してください。', 503);
        }
        if (!self::budget()) {
            if (is_array($stale)) { $stale['stale'] = true; return $stale; }
            return self::error('gh_rate', 'アクセスが集中しています。1分ほど待って再試行してください。', 429);
        }
        set_transient($lock, 1, 35);
        try { $result = call_user_func($loader); }
        finally { delete_transient($lock); }
        if (is_wp_error($result)) {
            set_transient($key . '_error', array('code' => $result->get_error_code(), 'message' => $result->get_error_message(), 'status' => $result->get_error_data()['status']), 60);
            if (is_array($stale)) { $stale['stale'] = true; return $stale; }
            return $result;
        }
        $result['stale'] = false;
        set_transient($key, $result, $ttl);
        set_transient($key . '_stale', $result, 86400);
        return $result;
    }
    private static function get_remote($url, $max_bytes) {
        // No user-supplied URLs or redirects: this is not a general-purpose proxy.
        $host = wp_parse_url($url, PHP_URL_HOST);
        if (!in_array($host, array('ja.wikipedia.org', 'news.google.com'), true)) {
            return self::error('gh_host', '取得先を確認できません。');
        }
        $r = wp_remote_get($url, array(
            'timeout' => 20, 'redirection' => 0, 'limit_response_size' => $max_bytes,
            'headers' => array('User-Agent' => 'GozaiHistory/1.0 (https://gozaigozai.com/ai-rekishi/)', 'Accept' => 'application/json, application/rss+xml;q=0.9'),
        ));
        if (is_wp_error($r)) { return self::error('gh_network', '外部サービスへ接続できません。時間をおいて再試行してください。'); }
        $status = wp_remote_retrieve_response_code($r);
        if ($status !== 200) { return self::error('gh_http', '外部サービスから取得できません（HTTP ' . (int) $status . '）。'); }
        $body = wp_remote_retrieve_body($r);
        if (strlen($body) >= $max_bytes) { return self::error('gh_size', '資料が大きすぎるため取得を中止しました。'); }
        return $body;
    }
    public static function history($request) {
        $year = $request['year']; $scope = $request['scope'];
        if (!self::valid_year($year) || !self::valid_scope($scope)) { return self::error('gh_args', '年または地域の指定を確認してください。', 400); }
        $year = (int) $year;
        return self::cached('gh_h_v1_' . $year . '_' . $scope, 3600, function() use ($year, $scope) {
            $title = $year . ($scope === 'japan' ? '年の日本' : '年');
            $url = 'https://ja.wikipedia.org/w/api.php?' . http_build_query(array('action' => 'parse', 'page' => $title, 'prop' => 'text|revid', 'format' => 'json', 'formatversion' => 2, 'redirects' => 1, 'disableeditsection' => 1), '', '&', PHP_QUERY_RFC3986);
            $raw = self::get_remote($url, 5000000);
            if (is_wp_error($raw)) { return $raw; }
            $data = json_decode($raw, true);
            if (isset($data['error']['code']) && $data['error']['code'] === 'missingtitle') {
                return self::error('gh_missing', 'Wikipediaに「' . $title . '」の個別記事がありません。別の年を選ぶか、比較する出来事を「世界」に切り替えてください。', 404);
            }
            if (!isset($data['parse']['text']) || !is_string($data['parse']['text'])) { return self::error('gh_parse', $year . '年の資料を取得できません。'); }
            $events = self::parse_events($data['parse']['text']);
            if (is_wp_error($events)) { return $events; }
            if (!$events) { return self::error('gh_empty', $year . '年の「出来事」を取得できません。別の年を選んでください。'); }
            $revision = isset($data['parse']['revid']) ? (int) $data['parse']['revid'] : 0;
            $page = 'https://ja.wikipedia.org/wiki/' . rawurlencode($title);
            return array('year' => $year, 'scope' => $scope, 'title' => $title, 'events' => $events, 'url' => $page, 'revision_url' => $revision ? 'https://ja.wikipedia.org/w/index.php?oldid=' . $revision : $page, 'retrieved_at' => gmdate('c'));
        });
    }
    private static function clean_text($node) {
        if ($node->nodeType === XML_TEXT_NODE) { return $node->nodeValue; }
        if ($node->nodeType !== XML_ELEMENT_NODE) { return ''; }
        if (in_array(strtolower($node->nodeName), array('script', 'style', 'sup', 'ul', 'ol'), true)) { return ''; }
        $text = '';
        foreach ($node->childNodes as $child) { $text .= self::clean_text($child); }
        return $text;
    }
    public static function parse_events($html) {
        if (!class_exists('DOMDocument')) { return self::error('gh_dom', 'サーバーのPHP DOM拡張が必要です。管理者にご確認ください。', 503); }
        $dom = new DOMDocument();
        $previous = libxml_use_internal_errors(true);
        $loaded = $dom->loadHTML('<?xml encoding="UTF-8">' . $html, LIBXML_NONET | LIBXML_NOERROR | LIBXML_NOWARNING);
        libxml_clear_errors(); libxml_use_internal_errors($previous);
        if (!$loaded) { return self::error('gh_html', '歴史資料を読み取れません。'); }
        $xpath = new DOMXPath($dom); $active = false; $events = array();
        foreach ($xpath->query('//h2 | //li') as $node) {
            if (strtolower($node->nodeName) === 'h2') {
                $label = trim($node->textContent);
                $active = (bool) preg_match('/^(できごと|出来事|Events)/u', $label);
                continue;
            }
            if (!$active || $xpath->query('.//li', $node)->length) { continue; }
            $parts = array(self::clean_text($node));
            for ($parent = $node->parentNode; $parent; $parent = $parent->parentNode) {
                if (strtolower($parent->nodeName) === 'li') { array_unshift($parts, self::clean_text($parent)); }
            }
            $text = trim(preg_replace('/\s+/u', ' ', implode(' ', $parts)));
            if (self::length($text) >= 8) { $events[] = self::truncate($text, 600); }
        }
        $events = array_values(array_unique($events));
        if (count($events) > 36) {
            $sample = array(); $last = count($events) - 1;
            // Match Python's round-to-even sampling exactly.
            for ($i = 0; $i < 36; $i++) { $sample[] = $events[(int) round($i * $last / 35, 0, PHP_ROUND_HALF_EVEN)]; }
            $events = $sample;
        }
        return $events;
    }
    public static function news($request) {
        $query = $request['q'];
        if (!self::valid_query($query)) { return self::error('gh_query', '検索語は1〜80文字で指定してください。', 400); }
        $query = trim(sanitize_text_field($query));
        if (!$query) { return self::error('gh_query', '検索語を入力してください。', 400); }
        return self::cached('gh_n_v1_' . md5($query), 900, function() use ($query) {
            $url = 'https://news.google.com/rss/search?' . http_build_query(array('q' => $query, 'hl' => 'ja', 'gl' => 'JP', 'ceid' => 'JP:ja'), '', '&', PHP_QUERY_RFC3986);
            $raw = self::get_remote($url, 1000000);
            if (is_wp_error($raw)) { return $raw; }
            if (!function_exists('simplexml_load_string')) { return self::error('gh_xml', 'サーバーのPHP XML拡張が必要です。', 503); }
            if (stripos($raw, '<!DOCTYPE') !== false || stripos($raw, '<!ENTITY') !== false) { return self::error('gh_xml', 'ニュースの形式を確認できません。'); }
            $previous = libxml_use_internal_errors(true);
            $xml = simplexml_load_string($raw, 'SimpleXMLElement', LIBXML_NONET | LIBXML_NOCDATA);
            libxml_clear_errors(); libxml_use_internal_errors($previous);
            if (!$xml || !isset($xml->channel)) { return self::error('gh_xml', 'ニュースを読み取れません。'); }
            $items = array();
            foreach ($xml->channel->item as $item) {
                $link = (string) $item->link;
                if (!in_array(wp_parse_url($link, PHP_URL_SCHEME), array('https', 'http'), true)) { continue; }
                $items[] = array('title' => wp_strip_all_tags((string) $item->title), 'url' => esc_url_raw($link));
                if (count($items) >= 5) { break; }
            }
            return array('query' => $query, 'items' => $items, 'retrieved_at' => gmdate('c'));
        });
    }
}
Gozai_History_App::init();
