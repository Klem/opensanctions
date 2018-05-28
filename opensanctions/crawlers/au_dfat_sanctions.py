from pprint import pprint  # noqa

import xlrd
from xlrd.xldate import xldate_as_datetime
from opensanctions.models import Entity
from normality import slugify


XLS_COLUMNS = [
    'reference',
    'name_of_individual_or_entity',
    'type',
    'name_type',
    'date_of_birth',
    'place_of_birth',
    'citizenship',
    'address',
    'additional_information',
    'listing_information',
    'committees',
    'control_date']


def parse_entry(context, data):
    rows = data.get('rows')
    primary = rows[0]
    if slugify(primary.get('type', '')) == 'individual':
        type_ = Entity.TYPE_INDIVIDUAL
    else:
        type_ = Entity.TYPE_ENTITY

    entity = Entity.create('au-dfat-sanctions', primary.get('reference'))
    entity.type = type_
    entity.url = 'http://dfat.gov.au/international-relations/security/sanctions/Pages/sanctions.aspx'  # noqa
    entity.name = primary.get('name_of_individual_or_entity', '')
    entity.program = primary.get('committees', '')
    entity.summary = primary.get('additional_information', '')

    country = primary.get('citizenship', '')
    if not isinstance(country, float):  # not NaN
        nationality = entity.create_nationality()
        nationality.country = country

    address = entity.create_address()
    address.text = primary.get('address', '')

    birth_date_text = primary.get('date_of_birth', '')
    if not isinstance(birth_date_text, float):
        birth_date = entity.create_birth_date()
        birth_date.date = birth_date_text

    birth_place_text = primary.get('place_of_birth', '')
    if not isinstance(birth_place_text, float):
        birth_place = entity.create_birth_place()
        birth_place.place = birth_place_text

    if rows[1:]:
        for row in rows[1:]:
            alias = entity.create_alias()
            alias.name = row.get('name_of_individual_or_entity', '')

    # pprint(entity.to_dict())
    context.emit(data=entity.to_dict())


def parse(context, data):
    res = context.http.rehash(data)
    xls = xlrd.open_workbook(res.file_path)
    ws = xls.sheet_by_index(0)

    header = [slugify(h, sep='_') for h in ws.row_values(0)]
    assert XLS_COLUMNS == header

    batch = []
    for r in range(1, ws.nrows):
        row = ws.row(r)
        row = dict(zip(header, row))
        for head, cell in row.items():
            if cell.ctype == 1:
                row[head] = cell.value
            elif cell.ctype == 2:
                row[head] = str(int(cell.value))
            elif cell.ctype == 3:
                date = xldate_as_datetime(cell.value, xls.datemode)
                row[head] = date.strftime('%m/%d/%y')
            elif cell.ctype == 0:
                row[head] = None
        if row.get('name_type') == 'Primary Name':
            batch = [row]
        elif row.get('name_type') == 'aka':
            batch.append(row)
        context.emit(data={
            'rows': batch
        })
