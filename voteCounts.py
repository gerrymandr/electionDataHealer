import os
import pandas as pd


class Fields(object):
    COUNTY_FIELD = 'County'
    DATE_FIELD = 'Election Date'
    PRECINCT_FIELD = 'Precinct'
    CONTEST_FIELD = 'Contest Name'
    CHOICE_FIELD = 'Choice'    # candidate name, write-in, over/under votes, etc.
    PARTY_FIELD = 'Party'
    ELECTION_DAY_VOTE_FIELD = 'Election Day'
    ONE_STOP_VOTE_FIELD = 'One Stop'
    ABSENTEE_VOTE_FIELD = 'Absentee'
    PROVISIONAL_VOTE_FIELD = 'Provisional'
    TOTAL_VOTE_FIELD = 'Total'

# TODO: move this into a metadata file. Consider using JSON or YAML for your configuration files
# in order to keep a hierarchical structure (as opposed to only flat columns). Both are supported
# by Python included libraries. YAML has the advantage that you can put comments into your file.
#
# For information on arguments to pandas.read_csv():
#  https://pandas.pydata.org/pandas-docs/stable/generated/pandas.read_csv.html
FIELD_MAPS = {
    'results_pct_20161108.txt': {
        'read_kwargs': {
            'sep': '\t',
            'header': 0,
            'infer_datetime_format': False,
            'index_col': False,
            'names': [
                Fields.COUNTY_FIELD,
                Fields.DATE_FIELD,
                Fields.PRECINCT_FIELD,
                'content group',
                'contest type',
                Fields.CONTEST_FIELD,
                Fields.CHOICE_FIELD,
                Fields.PARTY_FIELD,
                'vote for',
                Fields.ELECTION_DAY_VOTE_FIELD,
                Fields.ONE_STOP_VOTE_FIELD,
                Fields.ABSENTEE_VOTE_FIELD,
                Fields.PROVISIONAL_VOTE_FIELD,
                Fields.TOTAL_VOTE_FIELD,
            ],
        },
    },
    'results_sort_20161108.txt': {
        'read_kwargs': {
            'sep': '\t',
            'header': 0,
            'infer_datetime_format': False,
            'index_col': False,
            'names': [
                'county_id',
                Fields.COUNTY_FIELD,
                Fields.PRECINCT_FIELD,
                'precinct_desc',
                Fields.CONTEST_FIELD,
                'vote for',
                Fields.CHOICE_FIELD,
                Fields.TOTAL_VOTE_FIELD,
            ],
        },
    },
}


class VoteCounts(object):
    def __init__(self, dateInd, dataPath, prefix):
        basename = '{}{}.txt'.format(prefix, dateInd)
        config = FIELD_MAPS[basename]
        self.path = os.path.join(dataPath, basename)
        print(self.path)
        # The arguments for reading CSV come straight out of the config dictionary
        self.df = pd.read_table(self.path, **config['read_kwargs'])
