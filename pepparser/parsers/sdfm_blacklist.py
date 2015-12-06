from lxml import etree
from dateutil.parser import parse as dateutil_parse
from datetime import datetime

from pepparser.util import remove_namespace, make_id
from pepparser.text import combine_name
from pepparser.country import normalize_country


def parse_date(date):
    if date is None:
        return
    date = date.replace('.', '').strip()
    try:
        return dateutil_parse(date).date().isoformat()
    except:
        return


def get_names(aka):
    names = [aka.findtext('./aka-name1'),
             aka.findtext('./aka-name2'),
             aka.findtext('./aka-name3'),
             aka.findtext('./aka-name4')]
    names = [n for n in names if n is not None]
    data = {'other_name': combine_name(*names)}
    if not len(names):
        return data
    data['last_name'] = names[-1]
    names.remove(names[-1])
    if len(names) > 0:
        data['first_name'] = names[0]
    if len(names) > 1:
        data['second_name'] = names[1]
    if len(names) > 2:
        data['middle_name'] = names[2]
    return data


def parse_entry(emit, entry):
    uid = entry.findtext('number-entry')
    record = {
        'uid': make_id('ua', 'sdfm', uid),
        'type': 'individual',
        'publisher': 'State Financial Monitoring Service of Ukraine',
        'publisher_url': 'http://www.sdfm.gov.ua/',
        'source_url': 'http://www.sdfm.gov.ua/articles.php?cat_id=87&lang=en',
        'program': entry.findtext('./program-entry'),
        'summary': entry.findtext('./comments')
    }
    date_entry = entry.findtext('./date-entry')
    if date_entry:
        date_entry = datetime.strptime(date_entry, '%Y%m%d')
        record['updated_at'] = date_entry.date().isoformat()

    is_entity = entry.findtext('./type-entry') != '1'
    if is_entity:
        record['type'] = 'entity'

    record['other_names'] = []
    for aka in entry.findall('./aka-list'):
        data = get_names(aka)
        if aka.findtext('type-aka') == 'N':
            record['name'] = data.pop('other_name', None)
            record.update(data)
        else:
            data['type'] = aka.findtext('./type-aka')
            data['quality'] = aka.findtext('./quality-aka')
            if data['quality'] == '1':
                data['quality'] = 'strong'
            if data['quality'] == '2':
                data['quality'] = 'weak'
            # if is_entity:
            #     data.pop('last_name', None)
            record['other_names'].append(data)

    record['identities'] = []
    for doc in entry.findall('./document-list'):
        data = {
            'text': doc.findtext('./document-reg'),
            'number': doc.findtext('./document-id'),
            'country': normalize_country(doc.findtext('./document-country'))
        }
        record['identities'].append(data)

    for doc in entry.findall('./id-number-list'):
        data = {'text': doc.text.strip()}
        record['identities'].append(data)

    record['addresses'] = []
    for address in entry.findall('./address-list'):
        data = {
            'text': address.findtext('./address')
        }
        record['addresses'].append(data)

    # FIXME: handle multiple
    for pob in entry.findall('./place-of-birth-list'):
        record['place_of_birth'] = pob.text.strip()

    # FIXME: handle multiple
    for dob in entry.findall('./date-of-birth-list'):
        record['date_of_birth'] = parse_date(dob.text)

    # print etree.tostring(entry, pretty_print=True)
    # if is_entity:
    #     data.pop('last_name', None)
    #     data.pop('first_name', None)
    #     data.pop('second_name', None)
    #     data.pop('middle_name', None)
    emit.entity(record)


def sdfm_parse(emit, xmlfile):
    doc = etree.parse(xmlfile)

    for entry in doc.findall('.//acount-list'):
        parse_entry(emit, entry)
