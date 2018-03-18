import electionDataHealer as eDH
import os
import qgis

from PyQt4.QtCore import *

from qgis.core import *

qgs = eDH.initializeQGIS()

state = "NC" #select the state to use

#Code taken and put into bottom
dataHealer = eDH.electionDataHealer(state,relativeDataDir="../stateData")


elections = ["11/08/2016",
			 #"11/04/2014",
			 #"11/06/2012",           
		    ]

dataHealer.extractElectionData(elections)

dataHealer.finish()

eDH.finalizeQGIS(qgs)
