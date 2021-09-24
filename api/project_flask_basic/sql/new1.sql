CREATE TABLE users(
username CHAR(50) PRIMARY KEY,
password_hash VARCHAR(225) NOT NULL,
password_salt VARCHAR(10) NOT NULL,
created_on TIMESTAMP NOT NULL,
last_password_changed TIMESTAMP,
last_login TIMESTAMP
);

CREATE TABLE userextended(
    username CHAR(50) PRIMARY KEY REFERENCES users(username),
    first_name VARCHAR(50) NOT NULL,
    second_name VARCHAR(40),
    icon_photo_path VARCHAR(70) ,
    user_description VARCHAR(225) ,
	institution VARCHAR(40),
    teacher BOOLEAN,
    email VARCHAR(30),
    last_active TIMESTAMP,
	upload_folder VARCHAR(30)
	);

CREATE TABLE videometa(
    video_id varchar(100) PRIMARY KEY,
	username char(50) NOT NULL REFERENCES users(username),
	title char(300) NOT NULL,
	description char(2000),
	view_no integer NOT NULL,
	published TIMESTAMP,
	likes integer NOT NULL,
    video_file varchar(100),
	pres_file varchar(100)
);

CREATE TABLE videocomments(
	serial_c serial PRIMARY KEY,
	video_id varchar(100) NOT NULL REFERENCES videometa(video_id), 
	username char(50) NOT NULL REFERENCES users(username),
	published TIMESTAMP,
	contents char(2000)
	);

CREATE TABLE replies(
	serial_r serial PRIMARY KEY,
	video_id varchar(100) REFERENCES videometa(video_id),
	username char(50) REFERENCES users(username),
	serial_c integer REFERENCES videocomments(serial_c),
	published TIMESTAMP,
	contents char(2000)
);

create table usermsg(
serial_m BIGSERIAL PRIMARY KEY,
username CHAR(50) REFERENCES users(username) NOT NULL,
msg VARCHAR(500) NOT NULL,
published TIMESTAMP NOT NULL,
if_sentmail BOOL DEFAULT False
);

