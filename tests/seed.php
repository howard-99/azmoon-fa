<?php
// Integration fixture: explicit test marker and opt-in are both mandatory.
if (PHP_SAPI !== 'cli' || getenv('AZMOON_TEST') !== '1') exit(1);
$root=realpath($argv[1]??'');
if (!$root || !is_file($root.'/.azmoon-test')) exit(2);
chdir($root.'/public/code');
require_once '../../shared/config/tce_db_config.php';
$db=new mysqli(K_DATABASE_HOST,K_DATABASE_USER_NAME,K_DATABASE_USER_PASSWORD,K_DATABASE_NAME,(int)K_DATABASE_PORT);
$db->set_charset('utf8mb4');
$manager=(int)$db->query("SELECT user_id FROM tce_users WHERE user_level=10 LIMIT 1")->fetch_row()[0];
$hash=password_hash('Student-Test-123!',PASSWORD_BCRYPT);
$escaped=$db->real_escape_string($hash);
$db->query("INSERT INTO tce_users(user_regdate,user_ip,user_name,user_password,user_level,user_firstname,user_lastname) VALUES (NOW(),'127.0.0.1','student','$escaped',1,'سارا','احمدی'),(NOW(),'127.0.0.1','otherstudent','$escaped',1,'رضا','رضایی')");
$student=(int)$db->query("SELECT user_id FROM tce_users WHERE user_name='student'")->fetch_row()[0];
$other=(int)$db->query("SELECT user_id FROM tce_users WHERE user_name='otherstudent'")->fetch_row()[0];
$db->query("INSERT INTO tce_usrgroups VALUES ($student,1),($other,1)");
$db->query("UPDATE tce_modules SET module_enabled=1,module_user_id=$manager,module_name='آموزش عمومی' WHERE module_id=1");
$db->query("INSERT INTO tce_subjects(subject_module_id,subject_name,subject_description,subject_enabled,subject_user_id) VALUES (1,'دانش عمومی','مجموعه پرسش‌های نمونه برای بررسی رابط',1,$manager)");
$subject=$db->insert_id;
$definitions=[
 [1,'پایتخت ایران کدام شهر است؟','تهران پایتخت ایران است.',[['تهران',1],['مشهد',0],['شیراز',0],['اصفهان',0]]],
 [2,'کدام عددها زوج هستند؟','عدد زوج بر دو بخش‌پذیر است.',[['۲',1],['۳',0],['۴',1],['۵',0]]],
 [3,'یک جمله درباره یادگیری بنویسید.','پاسخ تشریحی توسط مدرس ارزیابی می‌شود.',[]],
 [4,'عددها را از کوچک به بزرگ مرتب کنید.','ترتیب صحیح یک، دو، سه است.',[['یک',0,1],['دو',0,2],['سه',0,3]]]
];
foreach ($definitions as $d) {
 $type=$d[0];$desc=$db->real_escape_string($d[1]);$ex=$db->real_escape_string($d[2]);
 $db->query("INSERT INTO tce_questions(question_subject_id,question_description,question_explanation,question_type,question_enabled) VALUES ($subject,'$desc','$ex',$type,1)");
 $qid=$db->insert_id;
 foreach($d[3] as $a){$text=$db->real_escape_string($a[0]);$right=$a[1];$pos=$a[2]??'NULL';$db->query("INSERT INTO tce_answers(answer_question_id,answer_description,answer_isright,answer_enabled,answer_position) VALUES ($qid,'$text',$right,1,$pos)");}
}
$db->query("INSERT INTO tce_tests(test_name,test_description,test_begin_time,test_end_time,test_duration_time,test_results_to_users,test_report_to_users,test_max_score,test_user_id,test_score_threshold,test_random_questions_select,test_random_questions_order,test_random_answers_select,test_random_answers_order,test_mcma_radio,test_questions_order_mode,test_answers_order_mode) VALUES ('آزمون دانش عمومی','چهار نوع سؤال برای بررسی ثبت پاسخ و کارنامه',DATE_SUB(NOW(),INTERVAL 1 DAY),DATE_ADD(NOW(),INTERVAL 1 DAY),30,1,1,4,$manager,2,0,0,0,0,0,2,2)");
$test=$db->insert_id;
$db->query("INSERT INTO tce_testgroups VALUES ($test,1)");
foreach([1,2,3,4] as $type){$db->query("INSERT INTO tce_test_subject_set(tsubset_test_id,tsubset_type,tsubset_quantity,tsubset_answers) VALUES ($test,$type,1,4)");$set=$db->insert_id;$db->query("INSERT INTO tce_test_subjects VALUES ($set,$subject)");}
fwrite(STDOUT,json_encode(['test_id'=>$test,'student_id'=>$student,'other_id'=>$other])."\n");
