<?php
// Semantics of review labels must match stored answer states.
require_once __DIR__.'/../payload/shared/azmoon/runtime.php';
function F_getBoolean($v){return in_array($v,[true,1,'1','t'],true);}
function expect($condition,$message){if(!$condition){fwrite(STDERR,$message."\n");exit(1);}}
$q=['question_type'=>1];
$right=['logansw_selected'=>1,'answer_isright'=>1];
$html=Azmoon_result_option($q,$right);
expect(str_contains($html,'انتخاب شما')&&str_contains($html,'پاسخ درست')&&str_contains($html,'az-selected'),'Selected correct MCSA');
$html=Azmoon_result_option($q,['logansw_selected'=>0,'answer_isright'=>1]);
expect(str_contains($html,'پاسخ درست')&&!str_contains($html,'az-selected'),'Unselected correct MCSA');
$html=Azmoon_result_option(['question_type'=>2],['logansw_selected'=>0,'answer_isright'=>0]);
expect(str_contains($html,'az-correct')&&str_contains($html,'علامت زده نشده'),'MCMA rejected distractor is correct');
$html=Azmoon_result_option(['question_type'=>2],['logansw_selected'=>-1,'answer_isright'=>1]);
expect(str_contains($html,'بی‌پاسخ')&&!str_contains($html,'az-correct'),'Unanswered MCMA remains unanswered');
$html=Azmoon_result_option(['question_type'=>4],['logansw_selected'=>0,'answer_isright'=>0,'logansw_position'=>2,'answer_position'=>1]);
expect(str_contains($html,'ترتیب شما: 2')&&str_contains($html,'ترتیب درست: 1'),'Ordering reports both positions');
expect(Azmoon_e('<script>')==='&lt;script&gt;','Brand HTML escaping');
echo "Review semantics and escaping: PASS\n";
