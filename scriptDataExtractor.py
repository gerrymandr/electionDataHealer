import electionDataHealer as eDH
import os
import qgis

from PyQt4.QtCore import *

from qgis.core import *

qgs = eDH.initializeQGIS()

state = "NC" #select the state to use

#Code taken and put into bottom
dataHealer = eDH.electionDataHealer(state,relativeDataDir="../StateData")


elections = [["11/08/2016",[["NC COMMISSIONER OF INSURANCE","COI16"],
			                ["NC GOVERNOR","GOV16"],
			               ]
			 ],
			 #["11/04/2014",[["US SENATE", "USS14"]]],
			 #["11/06/2012",[["PRESIDENT AND VICE PRESIDENT OF THE UNITED "\
			 #                +"STATES","PRE12"]]],
		    ]

dataHealer.extractElectionData(elections)

dataHealer.finish()

eDH.finalizeQGIS(qgs)
