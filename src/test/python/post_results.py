import xmltodict
from pymongo import MongoClient
import datetime
from smtplib import SMTP
import argparse
import urllib
import ruamel.yaml
import socket


def main():
    with open('results.xml') as fd:
        host = socket.gethostname()
        doc = xmltodict.parse(fd.read())
        tests = int(doc['testsuite']['@tests'])
        skips = int(doc['testsuite']['@skips'])
        errors = int(doc['testsuite']['@errors'])
        failures = int(doc['testsuite']['@failures'])
        time = doc['testsuite']['@time']
        msg = str(tests) + " tests, " + str(failures) + " failures, " + str(errors) + " errors, " + str(skips) + " skipped\n\n"
        errorlog = str()

        for testcase in doc['testsuite']['testcase']:
            print testcase['@classname']
            if 'failure' in testcase :
                errorlog += (testcase['failure']['#text']) +'\n'
                errorlog += '----------------------------------------------------\n'

        if args.mailserver:
            with open("watchers.yml", 'r') as f:
                recipients = ruamel.yaml.load(f, ruamel.yaml.RoundTripLoader)
                if failures > 0 or errors > 0:
                    email_addresses = [r['address'] for r in recipients if r['get_failure'] is True]
                    email_failures(host, email_addresses, msg, time, errorlog)
                else:
                    email_addresses = [r['address'] for r in recipients if r['get_success'] is True]
                    email_success(host, email_addresses, msg, time)
        if args.mongo_host and args.mongo_db and args.mongo_collection:
            report_mongo(host, "bd-api", "fence", tests, errors, failures, skips, msg, time, args.mongo_host, args.mongo_db, args.mongo_collection)



def report_mongo(host, hostname, type, total, errors, failures, skip, message, elapsed_time, mongo_host, mongo_db, mongo_collection):
    """Write the test results to mongo database"""
    document = {"host": host, "hostname": hostname, "type": type,
                "total": total, "success": total - errors - failures, "failures": errors + failures, "skipped": skip,
                "message": message,
                "elapsed_time": elapsed_time, "date": datetime.datetime.utcnow()}
    mc = MongoClient(mongo_host)
    db = mc[mongo_db]
    tests = db[mongo_collection]
    tests.insert(document)

def email_failures(from_host, email_addresses, msg, ellapsed_time, errorlog):
    message = 'From: \"' + from_host + '\" <devnull@ncsa.illinois.edu>\n'
    message += 'To: ' + ', '.join(email_addresses) + '\n'
    message += 'Subject: Brown Dog Tests Failed\n\n'
    message += 'Failures:\n\n'
    message += msg
    message += 'Elapsed time: ' + str(ellapsed_time)+ '\n'
    message += '++++++++++++++++++++++++++++++ ERROR LOG ++++++++++++++++++++++++++++++++++\n'
    message += errorlog

    mailserver = SMTP(args.mailserver)
    for watcher in email_addresses:
        mailserver.sendmail('', watcher, message)
    mailserver.quit()


def email_success(from_host, email_addresses, msg, ellapsed_time):
    message = 'From: \"' + from_host + '\" <devnull@ncsa.illinois.edu>\n'
    message += 'To: ' + ', '.join(email_addresses) + '\n'
    message += 'Subject: Brown Dog Tests Successful\n\n'
    message += 'Successes:\n\n'
    message += msg
    message += 'Elapsed time: ' + str(ellapsed_time)

    mailserver = SMTP(args.mailserver)
    for watcher in email_addresses:
        mailserver.sendmail('', watcher, message)
    mailserver.quit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--mongo_host")
    parser.add_argument("--mongo_db")
    parser.add_argument("--mongo_collection")
    parser.add_argument("--mailserver", default="localhost", help="mail server to send update emails out")
    args = parser.parse_args()
    # print args.echo
    main()