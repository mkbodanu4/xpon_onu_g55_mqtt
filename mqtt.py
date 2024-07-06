import paho.mqtt.publish as publish
import requests
import time
import yaml
import json
import re

session = requests.Session()

with open("configuration.yaml", 'r') as stream:
    configuration = yaml.safe_load(stream)

sleep_time = configuration['run']['sleep_time']

# Default values

auth_token = ''
rx_power_value = 0.0
tx_power_value = 0.0
loid_state_value = ''
supply_voltage_value = 0.0
bias_current_value = 0.0
temp_value = 0.0

PonSymPerAlarm_value = ''
PonFrameAlarm_value = ''
PonFraPerAlarm_value = ''
PonSecSumAlarm_value = ''
PonDygaspAlarm_value = ''
PonLinkAlarm_value = ''
PonCirEveAlarm_value = ''

# Regular expressions

rx_power_re = re.compile(r'var\ RxPower\ =\ \"(.*?)\"\;')
tx_power_re = re.compile(r'var\ TxPower\ =\ \"(.*?)\";')
loid_state_re = re.compile(r'Transfer\_meaning\(\'LoidState\'\,\'(.*?)\'\)\;')
supply_voltage_re = re.compile(r'\<td\ id\=\"Frm\_Volt\"\ name\=\"Frm\_Volt\"\ class\=\"tdright\"\>(.*?)\<\/td\>')
bias_current_re = re.compile(r'\<td\ id\=\"Frm\_Current\"\ name\=\"Frm\_Current\"[\s]{0,}class\=\"tdright\"\>(.*?)\<\/td\>')
temp_re = re.compile(r'\<td\ id\=\"Frm\_Temp\"\ name\=\"Frm\_Temp\"\ class\=\"tdright\"\>(.*?)\<\/td\>')

PonSymPerAlarm_re = re.compile(r'\<td\ id\=\"Frm_System\"\ name\=\"Frm_System\"\ class\=\"tdright\"\>(.*?)\<\/td\>')
PonFrameAlarm_re = re.compile(r'\<td\ id\=\"Frm_Frame\"\ name\=\"Frm_Frame\"\ class\=\"tdright\"\>(.*?)\<\/td\>')
PonFraPerAlarm_re = re.compile(r'\<td\ id\=\"Frm_FraPer\"\ name\=\"Frm_FraPer\"\ class\=\"tdright\"\>(.*?)\<\/td\>')
PonSecSumAlarm_re = re.compile(r'\<td\ id\=\"Frm_SecSu\"\ name\=\"Frm_SecSu\"\ class\=\"tdright\"\>(.*?)\<\/td\>')
PonDygaspAlarm_re = re.compile(r'\<td\ id\=\"Frm_Link\"\ name\=\"Frm_Link\"\ class\=\"tdright\"\>(.*?)\<\/td\>')
PonLinkAlarm_re = re.compile(r'\<td\ id\=\"Frm_Dygasp\"\ name\=\"Frm_Dygasp\"\ class\=\"tdright\"\>(.*?)\<\/td\>')
PonCirEveAlarm_re = re.compile(r'\<td\ id\=\"Frm_Link\"\ name\=\"Frm_Link\"\ class\=\"tdright\"\>(.*?)\<\/td\>')

login_token_re = re.compile(r'getObj\(\"Frm_Logintoken\"\).value\ \=\ \"(.*?)\"\;')
login_valid = re.compile(r'name\=\"mainFrame\"\ id\=\"mainFrame\"')

hostname = configuration['mqtt']['hostname']
auth = None
if configuration['mqtt']['username'] and configuration['mqtt']['password']:
    auth = {
        'username': configuration['mqtt']['username'],
        'password': configuration['mqtt']['password']
    }


def topic(name_value, component='sensor'):
    return 'homeassistant/' + component + '/g55_' + name_value


def name(sensor_name, prefix='XPON ONU ', suffix=''):
    return prefix + sensor_name + suffix


def friendly_name(sensor_name, prefix='', suffix=''):
    return prefix + sensor_name + suffix


def publish_multiple(msgs):
    try:
        publish.multiple(msgs=msgs, hostname=hostname, auth=auth)
    except Exception as e:
        print(e)


def publish_single(topic_value, payload):
    try:
        publish.single(topic=topic_value, payload=payload, hostname=hostname, auth=auth)
    except Exception as e:
        print(e)


def get_gpon_status_page():
    gpon_status_url = "http://" + configuration['onu']['ip'] + "/getpage.gch?pid=1002&nextpage=pon_status_link_info_t.gch"

    response = session.request('GET', url=gpon_status_url)
    if response.status_code != 200:
        publish_single(topic('parser_status/state'), 'Status Page Error ' + str(response.status_code))
        print("GET request to page " + gpon_status_url + " has status code " + str(response.status_code))
        return False

    is_logged = re.compile(r'logout\_redirect\(\)\;')
    if is_logged.search(response.text):
        publish_single(topic('parser_status/state'), 'Not authorized')
        print("Not authorized")
        return False

    return response.text


def get_gpon_alerts_page():
    gpon_alerts_url = "http://" + configuration['onu']['ip'] + "/getpage.gch?pid=1002&nextpage=epon_status_alarm_t.gch"

    response = session.request('GET', url=gpon_alerts_url)
    if response.status_code != 200:
        publish_single(topic('parser_status/state'), 'Alerts Page Error ' + str(response.status_code))
        print("GET request to page " + gpon_alerts_url + " has status code " + str(response.status_code))
        return False

    return response.text


def parse_gpon_status_page(content):
    global rx_power_value
    rx_power = rx_power_re.findall(content)
    if len(rx_power) > 0:
        rx_power_value = round(float(rx_power[0]) / 10000, 2)
    else:
        rx_power_value = 0.0

    global tx_power_value
    tx_power = tx_power_re.findall(content)
    if len(tx_power) > 0:
        tx_power_value = round(float(tx_power[0]) / 10000, 2)
    else:
        tx_power_value = 0.0

    global loid_state_value
    loid_state = loid_state_re.findall(content)
    if len(loid_state) > 0:
        loid_state_value_int = loid_state[0]

        if loid_state_value_int == '0':
            loid_state_value = 'Init State'
        elif loid_state_value_int == '1':
            loid_state_value = 'Authentication Success'
        elif loid_state_value_int == '2':
            loid_state_value = 'LOID is Wrong'
        elif loid_state_value_int == '3':
            loid_state_value = 'LOID OK , but password is wrong.'
        elif loid_state_value_int == '4':
            loid_state_value = 'LOID conflict'
        elif loid_state_value_int == '5':
            loid_state_value = 'Registration completed'
    else:
        loid_state_value = ''

    global supply_voltage_value
    supply_voltage = supply_voltage_re.findall(content)
    if len(supply_voltage) > 0:
        supply_voltage_value = round(float(supply_voltage[0]) / 1000000, 4)
    else:
        supply_voltage_value = 0.0

    global bias_current_value
    bias_current = bias_current_re.findall(content)
    if len(bias_current) > 0:
        bias_current_value = round(float(bias_current[0]) / 1000, 4)
    else:
        bias_current_value = 0.0

    global temp_value
    temp = temp_re.findall(content)
    if len(temp) > 0:
        temp_value = int(temp[0])
    else:
        temp_value = 0.0


def parse_gpon_alerts_page(content):
    global PonSymPerAlarm_value
    PonSymPerAlarm = PonSymPerAlarm_re.findall(content)
    if len(PonSymPerAlarm) > 0:
        PonSymPerAlarm_value = PonSymPerAlarm[0]
    else:
        PonSymPerAlarm_value = ''

    global PonFrameAlarm_value
    PonFrameAlarm = PonFrameAlarm_re.findall(content)
    if len(PonFrameAlarm) > 0:
        PonFrameAlarm_value = PonFrameAlarm[0]
    else:
        PonFrameAlarm_value = ''

    global PonFraPerAlarm_value
    PonFraPerAlarm = PonFraPerAlarm_re.findall(content)
    if len(PonFraPerAlarm) > 0:
        PonFraPerAlarm_value = PonFraPerAlarm[0]
    else:
        PonFraPerAlarm_value = ''

    global PonSecSumAlarm_value
    PonSecSumAlarm = PonSecSumAlarm_re.findall(content)
    if len(PonSecSumAlarm) > 0:
        PonSecSumAlarm_value = PonSecSumAlarm[0]
    else:
        PonSecSumAlarm_value = ''

    global PonDygaspAlarm_value
    PonDygaspAlarm = PonDygaspAlarm_re.findall(content)
    if len(PonDygaspAlarm) > 0:
        PonDygaspAlarm_value = PonDygaspAlarm[0]
    else:
        PonDygaspAlarm_value = ''

    global PonLinkAlarm_value
    PonLinkAlarm = PonLinkAlarm_re.findall(content)
    if len(PonLinkAlarm) > 0:
        PonLinkAlarm_value = PonLinkAlarm[0]
    else:
        PonLinkAlarm_value = ''

    global PonCirEveAlarm_value
    PonCirEveAlarm = PonCirEveAlarm_re.findall(content)
    if len(PonCirEveAlarm) > 0:
        PonCirEveAlarm_value = PonCirEveAlarm[0]
    else:
        PonCirEveAlarm_value = ''


def authenticate():
    global auth_token
    login_form_url = "http://" + configuration['onu']['ip'] + "/"

    login_form_response = session.request('GET', url=login_form_url)
    if login_form_response.status_code != 200:
        publish_single(topic('parser_status/state'), 'Authorization Error ' + str(login_form_response.status_code))
        print("GET request to page " + login_form_url + " has status code " + str(login_form_response.status_code))
        return False

    if not login_token_re.search(login_form_response.text):
        publish_single(topic('parser_status/state'), 'Login token not found')
        print("Login token not found")
        return False

    tokens = login_token_re.findall(login_form_response.text)

    if len(tokens) == 0:
        publish_single(topic('parser_status/state'), 'Login token not found')
        print("Login token not found")
        return False

    auth_token = tokens[0]

    login_request_response = session.request('POST', url=login_form_url, data={
        'frashnum': '',
        'action': 'login',
        'Frm_Logintoken': auth_token,
        'Username': configuration['onu']['username'],
        'Password': configuration['onu']['password'],
    })

    if login_request_response.status_code != 200:
        publish_single(topic('parser_status/state'), 'Authorization Error ' + str(login_request_response.status_code))
        print("POST request to page " + login_form_url + " has status code " + str(login_request_response.status_code))
        return False

    if not login_valid.search(login_request_response.text):
        publish_single(topic('parser_status/state'), 'Login unsuccessful')
        print("Login unsuccessful")
        return False

    return True


while True:
    sensors_definitions = [
        {
            'topic': topic('parser_status/config'),
            'payload': json.dumps({
                "name": name("Parser Status"),
                "state_topic": topic('parser_status/state'),
            })
        },
        {
            'topic': topic('auth_token/config'),
            'payload': json.dumps({
                "name": name("Login Token"),
                "state_topic": topic('auth_token/state'),
            })
        },
        {
            'topic': topic('rx_power/config'),
            'payload': json.dumps({
                "name": name("Optical Module Input Power"),
                "device_class": "signal_strength",
                "unit_of_measurement": "dBm",
                "state_topic": topic('rx_power/state'),
            })
        },
        {
            'topic': topic('tx_power/config'),
            'payload': json.dumps({
                "name": name("Optical Module Output Power"),
                "device_class": "signal_strength",
                "unit_of_measurement": "dBm",
                "state_topic": topic('tx_power/state'),
            })
        },
        {
            'topic': topic('loid_state/config'),
            'payload': json.dumps({
                "name": name("GPON State"),
                "state_topic": topic('loid_state/state'),
            })
        },
        {
            'topic': topic('supply_voltage/config'),
            'payload': json.dumps({
                "name": name("Optical Module Supply Voltage"),
                "device_class": "voltage",
                "unit_of_measurement": "V",
                "state_topic": topic('supply_voltage/state'),
            })
        },
        {
            'topic': topic('bias_current/config'),
            'payload': json.dumps({
                "name": name("Optical Transmitter Bias Current"),
                "device_class": "current",
                "unit_of_measurement": "mA",
                "state_topic": topic('bias_current/state'),
            })
        },
        {
            'topic': topic('temp/config'),
            'payload': json.dumps({
                "name": name("Operating Temperature of the Optical Module"),
                "device_class": "temperature",
                "unit_of_measurement": "°C",
                "state_topic": topic('temp/state'),
            })
        },
        {
            'topic': topic('PonSymPerAlarm/config'),
            'payload': json.dumps({
                "name": name("PonSymPerAlarm"),
                "state_topic": topic('PonSymPerAlarm/state'),
            })
        },
        {
            'topic': topic('PonFrameAlarm/config'),
            'payload': json.dumps({
                "name": name("PonFrameAlarm"),
                "state_topic": topic('PonFrameAlarm/state'),
            })
        },
        {
            'topic': topic('PonFraPerAlarm/config'),
            'payload': json.dumps({
                "name": name("PonFraPerAlarm"),
                "state_topic": topic('PonFraPerAlarm/state'),
            })
        },
        {
            'topic': topic('PonSecSumAlarm/config'),
            'payload': json.dumps({
                "name": name("PonSecSumAlarm"),
                "state_topic": topic('PonSecSumAlarm/state'),
            })
        },
        {
            'topic': topic('PonDygaspAlarm/config'),
            'payload': json.dumps({
                "name": name("PonDygaspAlarm"),
                "state_topic": topic('PonDygaspAlarm/state'),
            })
        },
        {
            'topic': topic('PonLinkAlarm/config'),
            'payload': json.dumps({
                "name": name("PonLinkAlarm"),
                "state_topic": topic('PonLinkAlarm/state'),
            })
        },
        {
            'topic': topic('PonCirEveAlarm/config'),
            'payload': json.dumps({
                "name": name("PonCirEveAlarm"),
                "state_topic": topic('PonCirEveAlarm/state'),
            })
        },
    ]

    publish_multiple(sensors_definitions)

    publish_single(topic('parser_status/state'), 'Working')

    time.sleep(sleep_time)

    sensors_data = []

    status_page_content = get_gpon_status_page()

    if not status_page_content:
        publish_single(topic('parser_status/state'), 'Authorizing')
        print("Authorizing")
        if authenticate():
            sensors_data.append({
                'topic': topic('auth_token/state'),
                'payload': str(auth_token)
            })

            status_page_content = get_gpon_status_page()
        else:
            publish_single(topic('parser_status/state'), "Can't authenticate")
            print("Can't authenticate")
            exit()

    parse_gpon_status_page(status_page_content)

    sensors_data.append({
        'topic': topic('rx_power/state'),
        'payload': str(rx_power_value)
    })
    sensors_data.append({
        'topic': topic('tx_power/state'),
        'payload': str(tx_power_value)
    })
    sensors_data.append({
        'topic': topic('loid_state/state'),
        'payload': str(loid_state_value)
    })
    sensors_data.append({
        'topic': topic('supply_voltage/state'),
        'payload': str(supply_voltage_value)
    })
    sensors_data.append({
        'topic': topic('bias_current/state'),
        'payload': str(bias_current_value)
    })
    sensors_data.append({
        'topic': topic('temp/state'),
        'payload': str(temp_value)
    })

    time.sleep(.1)

    alerts_page_content = get_gpon_alerts_page()
    parse_gpon_alerts_page(alerts_page_content)

    sensors_data.append({
        'topic': topic('PonSymPerAlarm/state'),
        'payload': str(PonSymPerAlarm_value)
    })
    sensors_data.append({
        'topic': topic('PonFrameAlarm/state'),
        'payload': str(PonFrameAlarm_value)
    })
    sensors_data.append({
        'topic': topic('PonFraPerAlarm/state'),
        'payload': str(PonFraPerAlarm_value)
    })
    sensors_data.append({
        'topic': topic('PonSecSumAlarm/state'),
        'payload': str(PonSecSumAlarm_value)
    })
    sensors_data.append({
        'topic': topic('PonDygaspAlarm/state'),
        'payload': str(PonDygaspAlarm_value)
    })
    sensors_data.append({
        'topic': topic('PonLinkAlarm/state'),
        'payload': str(PonLinkAlarm_value)
    })
    sensors_data.append({
        'topic': topic('PonCirEveAlarm/state'),
        'payload': str(PonCirEveAlarm_value)
    })

    publish_multiple(sensors_data)

    time.sleep(.1)
