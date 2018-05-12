# flaghunter
4chan Flag Tracker. Hunts for rare flags using the 4chan API.

## Understanding Limitations
It will save the number of runs and attendance to a pickle file, but will also write to a MariaDB database. Approximate max runtime is around 1500s. It will miss posts that have been made and deleted during runtime.
It saves the last seen flag per board, and doesn't search for the newest post until the last one it found
is 404'd. This speeds up the script and reduces API load, but means it will not always find the current post.

### Prerequisites

* Python 3
  * python3-pymysql
  * python3-requests
* MariaDB or equivalent
* PHP

### Installing

1.  Prepare the database and table:

```
CREATE DATABASE flags CHARACTER SET latin1 COLLATE latin1_general_ci;
USE flags;
CREATE TABLE country_flags2 (country CHAR(2), board VARCHAR(4), is_alive TINYINT(1) DEFAULT 0, postno INT(11), replyto INT(11), ratio DECIMAL(6,3));
ALTER TABLE country_flags2 ADD UNIQUE INDEX(board, country);
```

2.  Populate table with empty rows, for /pol/, /int/, /sp/, and /bant/:

```
LOAD DATA LOCAL INFILE './all_countries.txt' INTO TABLE country_flags2 SET board = 'pol';
```

3.  Edit the "db = pymysql.connect" line in flaghunter.py to se your MariaDB username and password

You may consider adding the script to crontab for automatic polling.

## Running

Once installed, simply run the script with the below command.

```
python3 flaghunter.py
```

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

* PK - inspiration for flaghunter
