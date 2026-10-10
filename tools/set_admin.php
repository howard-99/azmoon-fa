<?php
// Installer-only script. Reads passwords from environment, never from argv or logs.
if (PHP_SAPI !== 'cli') exit(1);
$root = realpath($argv[1] ?? '');
if (!$root || !is_file($root.'/shared/config/tce_db_config.php')) exit(2);
chdir($root.'/admin/code');
require_once '../../shared/config/tce_db_config.php';
$name = getenv('AZ_ADMIN_NAME'); $password = getenv('AZ_ADMIN_PASSWORD');
if (!is_string($name) || !preg_match('/^[A-Za-z][A-Za-z0-9_.-]{2,47}$/D', $name) || !is_string($password) || strlen($password)<12 || strlen($password)>72) {
    fwrite(STDERR, "Invalid administrator credentials\n"); exit(3);
}
$mysqli = new mysqli(K_DATABASE_HOST, K_DATABASE_USER_NAME, K_DATABASE_USER_PASSWORD, K_DATABASE_NAME, (int)K_DATABASE_PORT);
$hash = password_hash($password, PASSWORD_BCRYPT);
$stmt = $mysqli->prepare('UPDATE '.K_TABLE_USERS.' SET user_name=?, user_password=?, user_firstname=?, user_lastname=? WHERE user_name=? AND user_level=10');
$mysqli->set_charset('utf8mb4');
$first='مدیر';$last='سامانه';$old='admin';
$stmt->bind_param('sssss', $name, $hash, $first, $last, $old); $stmt->execute();
if ($stmt->affected_rows!==1) { fwrite(STDERR,"Default admin account not found\n"); exit(4); }
$stmt->close();
$mysqli->query("UPDATE ".K_TABLE_GROUPS." SET group_name='گروه عمومی' WHERE group_id=1");
$mysqli->query("UPDATE ".K_TABLE_MODULES." SET module_name='درس عمومی' WHERE module_id=1");
$mysqli->close();
fwrite(STDOUT,"Administrator created with a private password.\n");
