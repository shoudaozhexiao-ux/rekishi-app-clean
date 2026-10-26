<?php
// Isolated tests: no WordPress installation, credentials, or outbound requests.
define('ABSPATH', __DIR__ . '/');
class WP_Error {public $code;public $message;public $data;function __construct($c,$m,$d=array()){$this->code=$c;$this->message=$m;$this->data=$d;}}
function is_wp_error($v){return $v instanceof WP_Error;}
function add_action($a,$b){} function add_shortcode($a,$b){}
$GLOBALS['cache']=array();$GLOBALS['calls']=0;$GLOBALS['mode']='ok';$GLOBALS['enqueues']=array();
function get_transient($k){return isset($GLOBALS['cache'][$k])?$GLOBALS['cache'][$k]:false;}
function set_transient($k,$v,$ttl){$GLOBALS['cache'][$k]=$v;}
function delete_transient($k){unset($GLOBALS['cache'][$k]);}
function wp_parse_url($u,$c){return parse_url($u,$c);}
function wp_strip_all_tags($s){return strip_tags($s);}
function sanitize_text_field($s){return trim(strip_tags($s));}
function esc_url_raw($s){return $s;}
function plugins_url($p,$file){return 'https://gozaigozai.com/wp-content/plugins/gozai-history/'.$p;}
function rest_url($p){return 'https://gozaigozai.com/wp-json/'.$p;}
function wp_unique_id($p){static $i=0;return $p.(++$i);}
function esc_attr($s){return htmlspecialchars($s,ENT_QUOTES,'UTF-8');}
function esc_url($s){return esc_attr($s);}
function wp_enqueue_style($n,$u,$d,$v){$GLOBALS['enqueues'][$n]=$u;}
function wp_enqueue_script($n,$u,$d,$v,$footer){$GLOBALS['enqueues'][$n]=array($u,$d,$footer);}
function wp_remote_get($url,$args){
 $GLOBALS['calls']++;
 if($args['redirection']!==0)throw new Exception('Unexpected redirect policy');
 if(!in_array(parse_url($url,PHP_URL_HOST),array('ja.wikipedia.org','news.google.com'),true))throw new Exception('Unexpected host');
 $mode=$GLOBALS['mode'];
 if($mode==='network')return new WP_Error('network','internal details must not be exposed');
 if($mode==='redirect')return array('response'=>array('code'=>302),'body'=>'redirect');
 if(strpos($url,'news.google.com')!==false){
  $body=$mode==='entity'?'<!DOCTYPE rss [<!ENTITY x SYSTEM "file:///etc/passwd">]><rss/>':'<rss version="2.0"><channel><item><title><![CDATA[<img src=x onerror=alert(1)>ニュース]]></title><link>javascript:alert(1)</link></item><item><title>安全な記事</title><link>https://example.com/story</link></item></channel></rss>';
 }else{
  $body=json_encode($mode==='missing'?array('error'=>array('code'=>'missingtitle')):array('parse'=>array('revid'=>123,'text'=>'<h2>概要</h2><ul><li>これは除外される出来事</li></ul><div class="mw-heading"><h2>出来事</h2></div><ul><li>1月<ul><li>1日 - 鉄道が開通<sup>[1]</sup></li></ul></li><li>2月1日 - 映画が公開</li></ul><h2>フィクションのできごと</h2><ul><li>これは架空の出来事</li></ul>')));
 }
 return array('response'=>array('code'=>200),'body'=>$body);
}
function wp_remote_retrieve_response_code($r){return $r['response']['code'];}
function wp_remote_retrieve_body($r){return $r['body'];}
require __DIR__.'/../gozai-history/gozai-history.php';
function check($b,$m){if(!$b)throw new Exception($m);}
function reset_state(){$GLOBALS['cache']=array();$GLOBALS['calls']=0;$GLOBALS['mode']='ok';}
check(class_exists('DOMDocument'),'DOM is required for test');
check(Gozai_History_App::valid_year('1966'),'valid year');
check(!Gozai_History_App::valid_year('1966&url=x'),'reject injected year');
check(!Gozai_History_App::valid_year('1700'),'reject year outside bounds');
check(!Gozai_History_App::valid_scope('http://localhost'),'reject scope');
check(Gozai_History_App::valid_query(str_repeat('あ',80)),'UTF8 query bound');
check(!Gozai_History_App::valid_query(str_repeat('あ',81)),'long query rejected');
check(!Gozai_History_App::valid_query("a\nb"),'control character rejected');
$r=Gozai_History_App::history(array('year'=>1966,'scope'=>'japan'));
check(!is_wp_error($r),'history success');check($r['events']===array('1月 1日 - 鉄道が開通','2月1日 - 映画が公開'),'nested dates, real section and references');
check($r['title']==='1966年の日本' && $r['revision_url']==='https://ja.wikipedia.org/w/index.php?oldid=123','source and revision');
Gozai_History_App::history(array('year'=>1966,'scope'=>'japan'));check($GLOBALS['calls']===1,'fresh cache avoids requests');
unset($GLOBALS['cache']['gh_h_v1_1966_japan']);$GLOBALS['mode']='network';
$r=Gozai_History_App::history(array('year'=>1966,'scope'=>'japan'));check($r['stale']===true,'stale explicitly marked');
reset_state();$GLOBALS['mode']='missing';$r=Gozai_History_App::history(array('year'=>1966,'scope'=>'world'));check(is_wp_error($r),'missing year not invented');
Gozai_History_App::history(array('year'=>1966,'scope'=>'world'));check($GLOBALS['calls']===1,'failure cached');
reset_state();$GLOBALS['mode']='redirect';$r=Gozai_History_App::history(array('year'=>1966,'scope'=>'world'));check(is_wp_error($r),'redirect not followed');
reset_state();$GLOBALS['cache']['gh_budget_'.gmdate('YmdHi')]=60;$r=Gozai_History_App::history(array('year'=>1966,'scope'=>'world'));check(is_wp_error($r)&&$r->data['status']===429&&$GLOBALS['calls']===0,'upstream limit');
reset_state();$r=Gozai_History_App::news(array('q'=>'人工知能'));check(count($r['items'])===1&&$r['items'][0]['url']==='https://example.com/story','unsafe links dropped');
reset_state();$GLOBALS['mode']='entity';check(is_wp_error(Gozai_History_App::news(array('q'=>'人工知能'))),'XML external entities rejected');
$html='<h2>出来事</h2><ul>';for($i=0;$i<100;$i++)$html.='<li>出来事番号'.str_pad($i,3,'0',STR_PAD_LEFT).' - 説明文</li>';$html.='</ul>';
$events=Gozai_History_App::parse_events($html);check(count($events)===36&&strpos($events[0],'000')!==false&&strpos($events[35],'099')!==false,'whole-year sample');
$a=Gozai_History_App::shortcode();$b=Gozai_History_App::shortcode();check($a!==$b,'unique instances');check(strpos($a,'data-rest=')!==false,'endpoint configured');check($GLOBALS['enqueues']['gozai-history'][1]===array('gozai-history-core'),'script dependency');
echo "PASS: input limits, parser, nested dates, source revisions, cache, stale fallback, errors, upstream budget, XML safety, sampling, shortcode.\n";
