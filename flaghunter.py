#!/usr/bin/python3
# TODO: catch exception when there is not connection when pulling json. test by turning off internet
# pull the json for all specified thread, and active a column is_alive == "1" if it was seen.
# afterwards, either truncate or nullify all 404 rows.
# TODO: consider sticky threads and what to do with them.
# TODO: add time calculation in php to see how many minutes since last update
# TODO: consider sending email notification through php using sendmail application https://www.tutorialspoint.com/php/php_sending_emails.htm

# while debugging, delete total_threads.p from directory so it is a fresh run

import time
import requests
import pymysql
import pickle
#from tendo import singleton
#me = singleton.SingleInstance()

# global variables:
countries_text_path = './all_countries.txt'

# utility functions:

start_time = time.time()
# 1058 seconds when the list was moderately full
# 1056 s

# used to get json data for list of threads, and list of posts too
# returns list. 1.10 gave connection reset?
# 1.12 worked
sleep_time = 1.20
# sleep of 1.05 gave connection reset by peer, html error 104
def get_json(url):
    r = requests.get(url)
    time.sleep(sleep_time)
    return r.json()

# takes json, postno (int). expects for postno to be an OP (resto == 0)
# returns True if the post is in the json
def is_in_board_json(json, postno):
    result = False
    for page in json:  # starts from page 1, so that is okay
        for op in page['threads']:
            if postno == op['no']:  # thread is alive. set in table
                result = True
                return result

# takes thread json, postno (int)
# returns True if the post is in the json
def is_in_thread_json(json, postno):
    result = False
    for post in json['posts']:
        if postno == post['no']:
            result = True
            return result

# Open database connection. local-infile to allow reading and writing of local files by mysql queries
db = pymysql.connect("localhost", "username", "password", "flags", local_infile=1)

# prepare a cursor object using cursor() method
cursor = db.cursor(pymysql.cursors.DictCursor)

boards = ["pol", "int", "sp", "bant"]
sql_result = 0
try:
    sql = "SELECT NULL from country_flags2 limit 1;"  # returns 0 if empty set, 1 if nonempty
    sql_result = cursor.execute(sql)
    # Commit your changes in the database.
    db.commit()
except:
    # Rollback in case there is any error
    db.rollback()
if sql_result == 0:
    print("table is empty. populating...")
    for current_board in boards:
        try:
            sql = "LOAD DATA LOCAL INFILE '%s' " \
                  "INTO TABLE country_flags2 SET board = '%s';" % (countries_text_path, current_board)
            sql_result = cursor.execute(sql)
            # Commit the changes in the database.
            db.commit()
        except:
            # Rollback in case there is any error
            db.rollback()
# if above command worked, then the file exists
# try to open ratio file. if it doesnt exist, make a new one.
# also create temp boolean for counting towards ratio:
has_counted_flag = {}
try:
    with open('flag_checks.p', 'rb') as f:
        total_checks, flag_checks = pickle.load(f)
    country_file = open(countries_text_path, 'r')
    for line in country_file.readlines():
        has_counted_flag[line.replace("\n", "")] = False
except FileNotFoundError:
    flag_checks = {}
    total_checks = 0
    country_file = open(countries_text_path, 'r')
    for line in country_file.readlines():
        for current_board in boards:
            flag_checks[line.replace("\n", "")] = 0
        has_counted_flag[line.replace("\n", "")] = False
    with open('flag_checks.p', 'wb') as f:  # Python 3: open(..., 'wb')
        pickle.dump([total_checks, flag_checks], f)
country_file.close()

# set is_alive to 0 for all posts first
try:
    sql = "UPDATE country_flags2 SET is_alive=0;"
    sql_result = cursor.execute(sql)  # returns number of rows matching search query.
    # Commit the changes in the database.
    db.commit()
except:
    # Rollback in case there is any error
    db.rollback()

# all country rows are here now. check to see the rows have posts recorded, to ensure they are still alive
try:
    sql = "SELECT * FROM country_flags2 WHERE (replyto IS NOT NULL);"
    sql_result = cursor.execute(sql)  # returns number of rows matching search query.
    all_rows = cursor.fetchall()
    # Commit the changes in the database.
    db.commit()
except:
    # Rollback in case there is any error
    db.rollback()
# rows are store in cursor._rows as a tuple. use cursor = db.cursor(pymysql.cursors.DictCursor) if needed
posts_to_check = {'pol': dict(), 'int': dict(), 'sp': dict(), 'bant': dict()}  # key: board, value: unique thread resto

for post in all_rows:
    try:
        posts_to_check[post['board']][post['replyto']].add(post['postno'])
    except KeyError: # no thread resto yet, add it
        posts_to_check[post['board']][post['replyto']] = set()
        posts_to_check[post['board']][post['replyto']].add(post['postno'])

# traverse posts_to_check, set is_alive to True if spotted
for current_board in posts_to_check:
    for current_thread in posts_to_check[current_board]:
        thread_set = posts_to_check[current_board][current_thread]
        if current_thread == 0:  # if looking at OP posts
            try:
                alive_threads = get_json('http://a.4cdn.org/' + current_board + '/threads.json')
                for element in thread_set:  # element is postno
                    # if postno is in this json, activate is_alive in sql query
                    if is_in_board_json(alive_threads, element):
                        try:
                            sql = "UPDATE country_flags2 SET is_alive=1 " \
                                  "WHERE (board='%s') AND postno=%d;" % (current_board, element)
                            sql_result = cursor.execute(sql)  # returns number of rows matching search query.
                            # Commit the changes in the database.
                            db.commit()
                        except:
                            # Rollback in case there is any error
                            db.rollback()
            except (requests.ConnectionError, ValueError) as error:  # was assigned empty json since link was bad, or thread 404'd, or api banned
                continue
        elif current_thread != 0:
            try:
                replies = get_json('http://a.4cdn.org/' + current_board + '/thread/' + str(current_thread) + '.json')
                for element in thread_set:
                    if is_in_thread_json(replies, element):
                        try:
                            sql = "UPDATE country_flags2 SET is_alive=1 " \
                                  "WHERE (board='%s') AND postno=%d;" % (current_board, element)
                            sql_result = cursor.execute(sql)  # returns number of rows matching search query.
                            # Commit the changes in the database.
                            db.commit()
                        except:
                            # Rollback in case there is any error
                            db.rollback()
            except (requests.ConnectionError, ValueError) as error:  # was assigned empty json since link was bad, or thread 404'd
                continue

# we have set is_alive for all the posts still there. nullify all other rows now:
try:
    sql = "UPDATE country_flags2 SET postno = NULL, replyto = NULL WHERE is_alive=0;"
    sql_result = cursor.execute(sql)  # returns number of rows matching search query.
    # Commit the changes in the database.
    db.commit()
except:
    # Rollback in case there is any error
    db.rollback()

for current_board in boards:
    # grab list of alive threads, in ascending order to prevent 404'd shill threads
    try:
        alive_threads = get_json('http://a.4cdn.org/' + current_board + '/threads.json')
    except (requests.ConnectionError, ValueError) as error:  # was assigned empty json since link was bad, or thread 404'd
        continue
    for page in alive_threads:  # starts from page 1, so that is okay
        for op in page['threads']:
            try:
                replies = get_json('http://a.4cdn.org/' + current_board + '/thread/' + str(op['no']) + '.json')
            except ValueError:  # was assigned empty json since link was bad, or thread 404'd
                continue
            for reply in replies['posts']:
                # CONSIDER PUTTING SQL IN THE IF STATEMENT TO SAVE TIME AND SKIP WASTED UPDATES
                try:
                    if not has_counted_flag[reply['country']]:
                        flag_checks[reply['country']] += 1
                        has_counted_flag[reply['country']] = True
                    sql = "UPDATE country_flags2 SET is_alive=1, postno=%d, replyto=%d WHERE" \
                          " is_alive=0 AND country='%s' AND board='%s';" % \
                        (reply['no'], reply['resto'], reply['country'], current_board)
                except KeyError:  # note: mod can sometimes set no country. Note: /pol/ troll flags dont have 'country'
                    continue     # they are 'troll_country'. this exception skips these too.
                try:
                    # Execute the SQL command
                    sql_result = cursor.execute(sql) # returns 1 if added, 0 and/or warning if not added
                    if sql_result == 1:
                        # Commit your changes in the database.
                        db.commit()
                except:
                    # Rollback in case there is any error
                    db.rollback()

total_checks += 1
# write checks for next time.
with open('flag_checks.p', 'wb') as f:  # Python 3: open(..., 'wb')
    pickle.dump([total_checks, flag_checks], f)

# add ratios into table
for current_board in boards:
    for flag_string in flag_checks:
        ratio = 100 * (flag_checks[flag_string] / total_checks)
        ratio_stringed = '{number:.{digits}f}'.format(number=ratio, digits=3)
        try:
            sql = "UPDATE country_flags2 SET ratio=%s WHERE" \
                  " country='%s' AND board='%s';" % (ratio_stringed, flag_string, current_board)
            cursor.execute(sql)
            # Commit your changes in the database.
            db.commit()
        except:
            # Rollback in case there is any error
            db.rollback()

# disconnect from server
db.close()

print("%f seconds" % (time.time() - start_time))

