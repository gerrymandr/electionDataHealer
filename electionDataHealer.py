import codecs
import csv
import datetime
import glob
import numpy as np
import os
import platform
import qgis
import re

from collections import defaultdict
from PyQt4.QtCore import *
from qgis.core import *

def initializeQGIS():
    qgs = QgsApplication([], False)

    pathOptions = {'current': QgsApplication.prefixPath(),
                   'linux': '/usr',
                   'osx': '/Applications/QGIS.app/Contents/MacOS'}
    pathOptions['os_default'] = pathOptions[QgsApplication.osName()] if(QgsApplication.osName() in pathOptions) else ''
    pathChoiceDict = {'0': 'current', '1': 'os_default', '2': 'linux', '3': 'osx'}
    pathRequestString = 'Select your QGIS path:\n(0) Current value: ' + pathOptions['current'] + '\n(1) Your OS default (' + QgsApplication.osName() + '): ' + pathOptions['os_default'] + '\n(2) Linux default: ' + pathOptions['linux'] + '\n(3) OSX default: ' + pathOptions['osx'] + '\n(4) Other\n? '
    pathChoice = raw_input(pathRequestString)
    if(pathChoice in pathChoiceDict):
        qgs.setPrefixPath(pathOptions[pathChoiceDict[pathChoice]], True)
    else:
        qgs.setPrefixPath(raw_input('Enter your QGIS path: '), True)
    qgs.initQgis()
    return qgs

def finalizeQGIS(qgs):
    qgs.exitQgis()

class electionDataHealer:
    # Field names in metaShapeFileData.dat
    META_LEVEL = "Level"
    META_DATE = "Date"
    META_LOCATION = "Location"
    META_SOURCE = "Source"
    META_IS_DISTRICTING_PLAN = "DistrictingPlan_huh"
    META_COUNTY_ID = "CountyID"
    META_GEO_ID = "GEOID"

    def __init__(self,state,relativeDataDir="./",outputDir="./output/",qgisDir=""):
        #set shapefile directory
        self.state = state
        self.stateDataPath = relativeDataDir+"/"+state+"StateData/"

        #set and make output directory
        self.outputDir = outputDir
        if not os.path.exists(self.outputDir):
            os.makedirs(self.outputDir)

        if qgisDir!="":
            self.qgisDir = qgisDir
        else:
            system = platform.system()
            if system == "Darwin":
                self.qgisDir = "/Applications/QGIS.app/Contents/MacOS"
            else:
                print "Defaults for system", system, \
                      "have not been set yet (TO DO)"

        #set the county name to fips maps
        cfstr=self.stateDataPath+"/StateData/CountyFIPsCodes.txt"
        cntyf=open(cfstr)
        self.countyFIPStoNAME = {}
        self.countyNAMEtoFIPS = {}
        for line in cntyf:
            splitline = line.rstrip().split("\t")
            FIPS = splitline[1][-3:]
            NAME = splitline[0].upper()
            self.countyFIPStoNAME[FIPS] = NAME
            self.countyNAMEtoFIPS[NAME] = FIPS
        cntyf.close()
    #
    def extractElectionData(self,listOfElectionData):
        for electionDateIndex in range(len(listOfElectionData)):
            electionDate = listOfElectionData[electionDateIndex]
            print "Extracting election data from ", electionDate

            #get county list in current shapefile
            cntyList = self.countyNAMEtoFIPS.keys()
            #precinctGIDToVotes_Dict = self.getPctVoteCounts(electionDescp,
            #                                                electionDate,
            #                                                cntyList)
            pctGIDToFeat_Dict, pctLayer, pctMetaData = self.getFeaturesFromLayer(
                'Precinct', electionDate, cntyList)
            vtdGIDToFeat_Dict, vtdLayer, vtdMetaData = self.getFeaturesFromLayer(
                'VTD', electionDate, cntyList)
            #[vtdToPct, pctToVtd] = self.createVTDToPctDicts()  # LOH

            vtdToPct, pctToVtd = self.createVTDToPctDicts(
                                         vtdGIDToFeat_Dict,vtdLayer,vtdMetaData,
                                         pctGIDToFeat_Dict,pctLayer,pctMetaData)

            print 'precinctGIDToVotes_Dict:'
            print pctToVtd.keys()
            
            #precinctGIDToFeatAndVote_Dict = \
            #             self.mergePctVotesWithFeatures(electionDate,
            #                                            precinctGIDToVotes_Dict,
            #                                            pctGIDToFeat_Dict)
    #
    def mergePctVotesWithFeatures(self,date,pctGIDToVotes,pctGIDToFeats):
        dateInt = self.getDateInd(date)
        pctVoteFeat_Dict = {}
        curInd = 0
        while curInd < len(pctGIDToVotes.keys()):
            key = pctGIDToVotes.keys()[curInd]
            if key in pctGIDToFeats.keys():
                pctVoteFeat_Dict[key] = [pctGIDToVotes[key],pctGIDToFeats[key]]
                del pctGIDToVotes[key]
                del pctGIDToFeats[key]
            else:
                curInd+=1

        #delete sorted abs/prov/onestop/accum votes
        curInd = 0
        while curInd < len(pctGIDToVotes.keys()):
            key = pctGIDToVotes.keys()[curInd]
            if    "absentee" in key[1] or "accumulated" in key[1] \
               or "provisional" in key[1] or "curbside" in key[1] \
               or "transfer" in key[1] \
               or ("one" in key[1] and "stop" in key[1]) \
               or "misc" in key[1]:
                totRepDem = 0
                totCount  = 0
                for elecInd in range(pctGIDToVotes[key].shape[0]):
                    totRepDem += pctGIDToVotes[key][elecInd,0] + \
                                 pctGIDToVotes[key][elecInd,1]
                    totCount  += 1
                if totCount!=0 and totRepDem==0:
                    del pctGIDToVotes[key]
                else:
                    curInd+=1
            else:
                curInd+=1
        curInd = 0

        return pctVoteFeat_Dict
    #
    def getFeaturesFromLayer(self,level,electionDate,cntyList):
        GIDToFeature = {}
        print cntyList
        cntyNameList = [self.getCountyName(str(c)) for c in cntyList]
        dateInt   = self.getDateInd(electionDate)
        layerData = self.getPreexistingShapeFilePath(level,dateInt,verbose=True)
        layers    = self.loadShapefilesIntoLayers([layerData])
        shortName = self.getShortName(layerData)
        county_id = layerData[self.META_COUNTY_ID]
        geo_id = layerData[self.META_GEO_ID]
        for layer in layers:
            if layer.name()==shortName:
                curLayer = layer
        featureDict = {p.id():p for p in curLayer.getFeatures()}
        for p in featureDict.values():
            cnty = p[county_id].lower().replace("_"," ")
            if cnty in cntyNameList:
                pGID = p[geo_id]
                cntyFIPs = self.getCountyFIPS(cnty)
                GIDToFeature[(cntyFIPs,pGID.lower())] = p
        return GIDToFeature, curLayer, layerData
    #
    def createVTDToPctDicts(self,vtdIdToFeat,vtdLayer,vtdMetaData,
                                 pctIdToFeat,pctLayer,pctMetaData):
        
        vtdToPct = {}
        pctToVtd = defaultdict(list)

        #check intersections
        simKeys = set(pctIdToFeat.keys()) & set(vtdIdToFeat.keys())
        for key in simKeys:
            if   pctIdToFeat[key].geometry().area() \
               ==vtdIdToFeat[key].geometry().area() :
                vtdToPct[key] = key
                pctToVtd[key].append(key)
                del pctIdToFeat[key]
                del vtdIdToFeat[key]

        #Build a spatial index of the pcts 
        pctIndex = QgsSpatialIndex()
        for p in pctIdToFeat.values():
            pctIndex.insertFeature(p)

        #Build an FID to feature dict
        pctFIDToFeat  = { p.id():p for p in pctIdToFeat.values() }
        pctFIDToGEOID = { pctIdToFeat[p].id():p for p in pctIdToFeat.keys() }

        #Set up a coordinate transform to map from vtds to pcts
        tr = QgsCoordinateTransform(vtdLayer.crs(),pctLayer.crs())

        for vkey,vFeat in vtdIdToFeat.items():
            vGeom = vFeat.geometry()
            vGeom.transform(tr)
            intersectingIds = pctIndex.intersects(vGeom.boundingBox())

            areaRatios = []
            for indfeat in intersectingIds:
                pctfeat = pctFIDToFeat[indfeat]
                pctCnty = pctfeat[pctMetaData[self.META_COUNTY_ID]]
                pctCFIP = self.getCountyFIPS(pctCnty)
                if pctCFIP==vkey[0]:
                    pGeom   = pctfeat.geometry()
                    tmpUnion = pGeom.combine(vGeom)
                    areaRat  = (pGeom.area()+vGeom.area()-tmpUnion.area())/vGeom.area()
                    if areaRat>0:
                        areaRatios.append([areaRat,indfeat])
            maxRatio = 0
            indFeat  = 0

            if len(areaRatios)==0:
                raise Exception("error - no intersecting precincts found in v.id() {}".format(vkey))

            for item in areaRatios:
                if item[0]>maxRatio:
                    maxRatio=item[0]
                    indFeat=item[1]
            pctGeoId = pctFIDToGEOID[indFeat]
            vtdToPct[vkey] = pctGeoId
            pctToVtd[pctGeoId].append(vkey)
        return vtdToPct, pctToVtd

    def getPctVoteCounts(self,electionDate,cntyList,resultsPrefix):
        pctGIDToVoteCounts = {}
        cntyFIPSList = [self.getCountyFIPS(str(c)) for c in cntyList]
        dateInt = self.getDateInd(electionDate)
        voteFileStr = os.path.join(self.stateDataPath,"ElectionData",
                                   "results_sort_"+str(dateInt)+".txt")
        if not os.path.isfile(voteFileStr):
            print "ERROR: File", voteFileStr, "does not exist"
            exit()
        # voteFileUsortStr = os.path.join(self.stateDataPath,"ElectionData",
        #                                 "results_pct_"+str(dateInt)+".txt")
        # if not os.path.isfile(voteFileUsortStr):
        #     print "ERROR: File", voteFileUsortStr, "does not exist"
        #     exit()

        voteFile = open(voteFileStr)
        keyLine  = voteFile.readline().rstrip().replace('\"','').lower()
        keyLine  = re.split("\t|,",keyLine)

        [cntyKey,pctKey,contestKey,voteCountKey,partyKey,partyDict,
         csvReaderInfo] = self.getSortedVTDKeys(keyLine,dateInt,voteFileUsortStr)

        for line in voteFile:
            #hack to eliminate null characters
            line = line.replace("\0","")
            #then split the line
            for sl in csv.reader([line],quotechar=csvReaderInfo[0],
                           delimiter=csvReaderInfo[1],quoting=csvReaderInfo[2]):
                splitline = sl
            cntyFIPs  = self.getCountyFIPS(splitline[cntyKey])
            contest   = splitline[contestKey].upper()

            if cntyFIPs in cntyFIPSList and\
               contest in electionDescp:
                contestInd = electionDescp.index(contest)
                try:
                    party = partyDict[splitline[partyKey].lower()]
                except:
                    party = "noparty"
                if "dem" == party.lower():
                    partyInd = 0
                elif "rep" == party.lower():
                    partyInd = 1
                else:
                    partyInd = 2
                if cntyFIPs == "129" and contest=="US SENATE":
                    print splitline, party, partyInd, splitline[partyKey].lower(), partyKey
                precinctID = splitline[pctKey]
                totalVotes = int(splitline[voteCountKey])
                key = (cntyFIPs,precinctID.lower())
                if key not in pctGIDToVoteCounts.keys():
                    pctGIDToVoteCounts[key] = np.zeros((len(electionDescp),3),
                                                        dtype=int)
                pctGIDToVoteCounts[key][contestInd,partyInd]+=totalVotes
        voteFile.close()
        return pctGIDToVoteCounts
        #cntyKey      = keyLine.index("county")
        #pctKey       = keyLine.index("precinct")
        #contestKey   = [i for i, s in enumerate(keyLine)
        #                               if ( 'contest' == s or
        #                                   ('contest' in s and 'name' in s))][0]
        #voteCountKey = keyLine.index("total votes")
        #partyKey     = [i for i, s in enumerate(keyLine) if 'party' in s][0]
    #
    def getSortedVTDKeys(self,keyLine,dateInd,voteFileUsortStr):
        if dateInd==20121106:
            cntyKey      = keyLine.index("county")
            pctKey       = keyLine.index("vtd")
            contestKey   = keyLine.index("contest")
            voteCountKey = keyLine.index("total votes")
            partyKey     = keyLine.index("party")
            partyDict    = {"dem":"dem","rep":"rep"}
            csvDelimiterInfo = ['\"',',',csv.QUOTE_ALL]
        elif dateInd==20141104:
            cntyKey      = keyLine.index("county")
            pctKey       = keyLine.index("precinct")
            contestKey   = keyLine.index("contest name")
            voteCountKey = keyLine.index("total votes")
            partyKey     = keyLine.index("choice party")
            partyDict    = {"dem":"dem","rep":"rep"}
            csvDelimiterInfo = ['','\t',csv.QUOTE_NONE]
        elif dateInd==20161108:
            cntyKey      = keyLine.index("county_desc")
            pctKey       = keyLine.index("precinct_code")
            contestKey   = keyLine.index("contest_name")
            voteCountKey = keyLine.index("votes")
            partyKey     = keyLine.index("candidate_name")
            partyDict    = self.buildPartyDict(voteFileUsortStr,"choice",
                                                           "choice party")
            csvDelimiterInfo = ['','\t',csv.QUOTE_NONE]

        return [cntyKey,pctKey,contestKey,voteCountKey,partyKey,partyDict,
                csvDelimiterInfo]
    #
    def buildPartyDict(self,partyFileStr,contName,partyName):
        partyDict = {}
        partyFile = open(partyFileStr)

        keyLine = partyFile.readline().rstrip().replace('\"','').lower()
        keyLine = re.split("\t|,",keyLine)

        contKey = keyLine.index(contName)
        partyKey = keyLine.index(partyName)

        for line in partyFile:
            splitline = line.rstrip().replace('\"','').lower()
            splitline = re.split("\t|,",splitline)
            contestant = splitline[contKey]
            party      = splitline[partyKey].upper()
            partyDict[contestant] = party
        partyFile.close()

        return partyDict
    #
    def getCountyFIPS(self,cntyDesc):
        try:
            return self.countyNAMEtoFIPS[cntyDesc.upper()]
        except:
            return cntyDesc.zfill(3)
    #
    def getCountyName(self,cntyDesc):
        try:
            return self.countyFIPStoNAME[cntyDesc.zfill(3)].lower()
        except:
            return cntyDesc.lower()
    #
    def getCountyFIPFieldName(self):
        self.testInitialize()
        fndField = False
        fieldNames = [field.name() for field in
                      self.extractLayer.pendingFields()]
        for fieldName in fieldNames:
            fnlow = fieldName.lower()
            if     ("county" in fnlow or "cnty" in fnlow) \
               and ("fp" in fnlow or "fip" in fnlow):
                try:
                    int(self.feature_dict[self.feature_dict.keys()[0]]
                                         [fieldName])
                    countyField = fieldName
                    fndField = True
                except:
                    continue
        if not fndField:
            print "ERROR: could not find county field name in layer", \
                  self.extractLayer.name()
            exit()
        return countyField
    #
    @staticmethod
    def getDateInd(date=""):
        if len(date)!=10 and len(date)!=0:
            raise Exception("error: the date must be empty or in the form 'MM/DD/YYYY'; is in the form {}".format(date))
            exit()
        elif len(date)==0:
            now    = datetime.datetime.now()
            dateInt= int(str(now.year)+str(now.month).zfill(2)+
                      str(now.day).zfill(2))
        else:
            splitDate = date.split("/")
            dateInt = int(splitDate[2]+splitDate[0]+splitDate[1])
        return dateInt
    #
    def getPreexistingShapeFilePath(self,level,dateInt,districtingPlan=False,
                                    verbose=False):
        shapeMetaData=open(self.stateDataPath+"/metaShapeFileData.dat")
        def parseLine(line):
            return line.rstrip().split("\t")
        fieldnames = parseLine(shapeMetaData.readline())
        curDateInt = 0
        lineToUse = ["County","","","","","",""]
        for line in shapeMetaData:
            splitline = parseLine(line)
            # Create a dict mapping field names to the line values
            fields = dict(zip(fieldnames, splitline))
            if fields[self.META_IS_DISTRICTING_PLAN]=="False":
                curDistPlan = False
            elif fields[self.META_IS_DISTRICTING_PLAN]=="True":
                curDistPlan = True
            else:
                raise Exception("error: shapefiles are either districting plans or not\n"
                                "error found in metaShapeFileData.dat, line: {}".format(line))
            if level==fields[self.META_LEVEL] and districtingPlan==curDistPlan:
                testDateInt = self.getDateInd(fields[self.META_DATE])
                if testDateInt <= dateInt and testDateInt > curDateInt:
                    curDateInt = testDateInt
                    lineToUse = fields
        shapeMetaData.close()

        if verbose:
            print "Using pre-existing shapefile data:"
            print "  Level:", lineToUse[self.META_LEVEL]
            print "  Date:", lineToUse[self.META_DATE]
            print "  Shapefile:", lineToUse[self.META_LOCATION]
            print "  Source:", lineToUse[self.META_SOURCE]
        return lineToUse
    #
    def loadShapefilesIntoLayers(self,shapefileList):
        layers = QgsMapLayerRegistry.instance().mapLayers().values()
        curDir = os.getcwd()
        for LAYER_NAME in shapefileList:
            shortName = self.getShortName(LAYER_NAME)
            layerLoaded = False
            for layerQ in layers:
                if layerQ.name() == shortName:
                    layerLoaded = True
            location = LAYER_NAME[self.META_LOCATION]
            if not layerLoaded and location!="":
                regexShapeFilePath = curDir+"/"+self.stateDataPath +\
                                     "/Shapefiles/" + location+"/*.shp"
                shapefilePos  = glob.glob(regexShapeFilePath)
                if len(shapefilePos)>1:
                    print "WARNING: Multiple shapefiles found in layer name",\
                          LAYER_NAME, ":", shapefilePos
                shapefilePath = shapefilePos[0]
                newlayer = QgsVectorLayer(shapefilePath, shortName, "ogr")
                if not newlayer.isValid():
                    print "Layer failed to load!  You may need to supply a different QGIS path."
                    exit()
                # add the layer to the registry
                QgsMapLayerRegistry.instance().addMapLayer(newlayer)

                # refresh the layers list
                layers = QgsMapLayerRegistry.instance().mapLayers().values()
        return layers
    #
    def resetOutputDir(self,outputDir="./"):
        #set and make output directory
        self.outputDir = outputDir
        if not os.path.exists(self.outputDir):
            os.makedirs(self.outputDir)
    #
    @classmethod
    def getShortName(cls, metaline):
        return metaline[cls.META_LEVEL]+str(cls.getDateInd(metaline[cls.META_DATE]))
