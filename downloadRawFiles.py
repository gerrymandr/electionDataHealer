import luigi
import urllib
import zipfile


class SortedDataRaw(luigi.ExternalTask):
    date = luigi.DateParameter()

    def output(self):
        return luigi.LocalTarget('../stateData/NC/results/sorted/{}.zip'
                                 .format(self.date.strftime('%Y%m%d')))
    
    def run(self):
        url = 'https://s3.amazonaws.com/dl.ncsbe.gov/ENRS/{}/results_sort_{}.zip'.format(
            self.date.strftime('%Y_%m_%d'),
            self.date.strftime('%Y%m%d')
        )
        urllib.urlretrieve(url, self.output().path)


class UnzippedSortedData(luigi.Task):
    date = luigi.DateParameter()
    
    def requires(self):
        return [SortedDataRaw(date=self.date)]
    
    def output(self):
        return luigi.LocalTarget('../stateData/NC/results/sorted/results_sort_{}.txt'
                                 .format(self.date.strftime('%Y%m%d')))

    def run(self):
        for infile in self.input():
            z = zipfile.ZipFile(infile.path)
            z.extractall('../stateData/NC/results/sorted/')        

            
if __name__ == '__main__':
    luigi.run()
