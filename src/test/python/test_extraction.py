import requests
from os.path import basename, splitext
import sys
import json
import time
import urllib2
import pytest

# @pytest.mark.skip(reason="testing conversions")
def test_get_extract(host, api_token, timeout, extraction_data):
    print(extraction_data['description'])
    endpoint = host + '/dts/api'
    input_url = extraction_data['file_url']
    output = extraction_data['output']
    metadata = extract_by_url(endpoint, api_token, input_url, timeout)
    print("Extraction output " + metadata)
    if output.startswith("http://"):
        output = urllib2.urlopen(output).read().strip()
    assert metadata.find(output) != -1


def extract_by_url(endpoint, api_token, input_url, timeout):
    metadata = json.dumps({})
    headers = {'Authorization': api_token, 'Content-Type': 'application/json'}
    api_call = endpoint + '/extractions/upload_url'
    print("POST " + api_call)
    try:
        r = requests.post(api_call, headers=headers, timeout=timeout, data=json.dumps({"fileurl":input_url}))
        if r.status_code != 200:
            print("ERROR: " + r.text)
            return ""
        else:
            file_id = r.json()['id']
            print("File id " + file_id)
            # Poll until output is ready (optional)
        while timeout > 0:
            status = requests.get(endpoint + '/extractions/' + file_id + '/status', headers=headers, timeout=timeout).json()
            if status['Status'] == 'Done':
                print("Status: Done")
                break
            else:
                print("Status: " + status['Status'])
            time.sleep(1)
            timeout -= 1

        # Display extracted content (TODO: needs to be one endpoint)
        metadata = requests.get(endpoint + '/extractions/' + file_id + '/metadata', headers=headers, timeout=timeout).json()
        metadata["technicalmetadata"] = requests.get(endpoint + '/files/' + file_id + '/technicalmetadatajson', headers=headers, timeout=timeout).json()
        metadata["metadata.jsonld"] = requests.get(endpoint + '/files/' + file_id + '/metadata.jsonld', headers=headers, timeout=timeout).json()
        metadata = json.dumps(metadata)

        # Delete test files
        requests.delete(endpoint + '/files/' + file_id, headers=headers, timeout=timeout)
    except KeyboardInterrupt:
        sys.exit()
    except:
        e = sys.exc_info()[0]
        print repr(e)
    return metadata





