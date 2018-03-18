from datetime import date
from luigi import Task, ExternalTask, WrapperTask
from luigi import DateParameter, Parameter, LocalTarget
import luigi
import urllib
import zipfile

#TODO: Make directories as needed.


class DownloadFromUrl(object):
    """A base class with a common run method.
    """
    BASE_URL = 'https://s3.amazonaws.com/dl.ncsbe.gov/'

    def run(self):
        urllib.urlretrieve(self.url(), self.output().path)


class SortedDataRaw(DownloadFromUrl, ExternalTask):
    date = DateParameter()

    def output(self):
        return LocalTarget('../StateData/NC/sorted/{}.zip'
                                 .format(self.date.strftime('%Y%m%d')))

    def url(self):
        url = self.BASE_URL + 'ENRS/{}/results_sort_{}.zip'.format(
            self.date.strftime('%Y_%m_%d'),
            self.date.strftime('%Y%m%d')
        )
        return url


class UnzippedSortedData(Task):
    date = DateParameter()

    def requires(self):
        return [SortedDataRaw(date=self.date)]

    def output(self):
        return LocalTarget('../StateData/NC/sorted/results_sort_{}.txt'
                                 .format(self.date.strftime('%Y%m%d')))

    def run(self):
        for infile in self.input():
            z = zipfile.ZipFile(infile.path)
            z.extractall('../StateData/NC/sorted/')        

class AllUnzippedSortedData(WrapperTask):
    def requires(self):
        """These dates come from those listed at
        https://dl.ncsbe.gov/?prefix=ENRS/
        Which actually have a results_sort*.zip file.
        """
        dates = [date(*map(int, x.split('_'))) for x in ['2008_05_06', '2008_06_24',
                                    '2008_11_04',
                                    '2009_09_15', '2009_10_06',
                                    '2009_11_03', '2010_05_04', '2010_06_22',
                                    '2010_11_02', '2011_09_13', '2011_10_11',
                                    '2012_05_08', '2012_07_17',
                                    '2012_11_06', '2013_09_10', '2013_10_08',
                                    '2013_11_05', '2014_05_06', '2014_07_15',
                                    '2014_11_04', '2015_05_12', '2015_09_15',
                                    '2015_10_06', '2015_11_03', '2016_03_15',
                                    '2016_11_08']]
        for valid_nc_date in dates:
            yield UnzippedSortedData(date=valid_nc_date)
            

class ShapeData(DownloadFromUrl, ExternalTask):
    date = DateParameter()
    level = Parameter(default = 'VTD')
    ftp_date_format = Parameter(default = '%Y%m%d')

    def output(self):
        return LocalTarget('../StateData/NC/shapefiles/SBE_{}_{}.zip'
                           .format(self.level, self.date.strftime('%Y%m%d')))

    def url(self):
        return self.BASE_URL + 'ShapeFiles/{}/SBE_{}_{}.zip'.format(
            self.level, self.level,
            self.date.strftime(self.ftp_date_format)
        )

class AllVTDData(WrapperTask):
    def requires(self):
        """These dates come from those listed at
        https://dl.ncsbe.gov/?prefix=ShapeFiles/VTD
        """
        dates = [(date(2015,9,10), ),
                 (date(2012,9,12), '%m%d%Y')]

        for d in dates:
            kwargs = dict(zip(('date', 'ftp_date_format'), d))
            yield ShapeData(**kwargs)


if __name__ == '__main__':
    luigi.run()
