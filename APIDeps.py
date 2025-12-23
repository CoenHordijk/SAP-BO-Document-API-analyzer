import xml.etree.ElementTree as ET
from lxml import etree
import re
import pandas as pd
import requests
import time
import html
import getpass

global GLlogonToken, GLheaders, GLRequestCount


# This variable contains the baseURL string for API access
# Change it to your organisation base URL for SAP BO

# Enter your servername
CNenvironment = 'https://<SERVERNAME>'

# Enter path to biprws on the server
CNbaseURL = '/<SOMEPATH>/biprws'

# for document requests
CNdocURL = '/raylight/v1/'

# Document URL is created of these 3 parts
CNdocumentURL = CNenvironment + CNbaseURL + CNdocURL + ''

# SSL
CNverify = True

# enter your auth. method
CNautmethod = 'secEnterprise'
# CNautmethod = 'secWinAD'

#  API response timout (seconds)
CNapi_timeout = 8


CNlogonheader = {
        'Content-Type': 'application/xml',
    	'Accept': 'application/xml'
	}  


def getAPIResponse(requestURL, catchError = 0):
# universal function for api GET requests    
    
    # print(GLheaders)
    global GLRequestCount
    
    responsetext = ''

    try:
        response = requests.get(requestURL, headers = GLheaders, verify = CNverify, timeout = CNapi_timeout)

        # inserted this statement to properly convert textst containing 'ë' 
        response.encoding = response.apparent_encoding
        responsetext = response.text

        GLRequestCount = GLRequestCount + 1
    
        if responsetext.find('<error>') >0:
            responsetext = '<xml></xml>'
            if catchError == 0:
                print('response error for ', requestURL, response.text)
            # time.sleep(50)
    except:

        responsetext = '<xml></xml>'
        
        if catchError == 0:
            print('API response time out (', CNapi_timeout, ' sec. )')
            print('request URL: \n', requestURL)

    # Standard delay after each request to relieve the API service
    time.sleep(0.05)

    return responsetext

    
def logonSAP():

    global GLheaders,  GLlogontoken, GLRequestCount, GLcmsqueryheader

    
    print('Login in to', CNenvironment)
    print()

    username = input(' Username: ')
    password = getpass.getpass(prompt = ' Password: ')


    requestbody = '''<attrs xmlns="http://www.sap.com/rws/bip"> 
            <attr name="clienttype" type="string"></attr>
            <attr name="auth" type="string">''' + CNautmethod + '''</attr>
            <attr name="userName" type="string">''' + username + '''</attr>
            <attr name="password" type="string">''' + password + '''</attr>
        </attrs>'''

    reqURL = CNenvironment + CNbaseURL + '/logon/long'

    logonresponse = requests.post(reqURL, headers = CNlogonheader, data = requestbody,  verify = CNverify)

    logonstatus = logonresponse.status_code

    print()
    if logonstatus == 200:
        print('Login succesful')

        GLRequestCount = 0

        logonxml = ET.fromstring(logonresponse.text)
        GLlogontoken = logonxml[3][0][0].text

        # Set the global variabele for use in all API requests
        # nb x-sap-pvl (language setting) does not seem te work
        # 'Cache-Control': 'no-cache' does not seem to work either
        
        GLheaders = {
            'Content-Type': 'application/xml',
        	'Accept': 'text/html, application/xhtml+xml, application/xml;q=0.9, image/webp, */*;q=0.8',
        	'X-SAP-LogonToken': GLlogontoken,
            'X-SAP-PVL' : 'nl-NL'
    	}       

        GLcmsqueryheader = {
            'X-SAP-LogonToken': GLlogontoken,
            'Content-Type': 'application/xml',
        	'Accept': 'text/html, application/xhtml+xml, application/xml;q=0.9, image/webp, */*;q=0.8',
    	}  

    else:
        print('Login failed (response code: ', str(logonstatus), ')')

    
def DictToList(dict):
    
    mylist = []   
    for k in dict:
        mylist.append(dict[k])

    return mylist


def getDocumentProperties(docID):
# gets the document properties, returns them in a dictionary

    props = {}

    subreqURL = 'documents/' + str(docID) + '/properties'

    response = getAPIResponse(CNdocumentURL + subreqURL)

    vd_root = ET.fromstring(response)
    
    for prop in vd_root.findall(".//property"):
        key = prop.attrib['key']
        props[key] = prop.text

    return props


def getSpecificDocProps(docID):
# select lastupdate and lastupdateby from document properties    
    propdict = getDocumentProperties(docID)

    lastmod = ''
    modby = ''
    docname = ''
    docpath = ''

    
    if 'name' in propdict:
        docname = propdict['name']

    if 'lastsavedby' in propdict:
        docpath = propdict['path']

    
    if 'modificationdate' in propdict:
        lastmod = propdict['modificationdate']

    if 'lastsavedby' in propdict:
        modbyID = propdict['lastsavedby']

    modby = modbyID
    
    return docname, docpath, lastmod, modby


def getDocumentAlerters(docID):
# 
    
    # First get the document dataprovider IDs
    subreqURL = 'documents/' + str(docID) + '/alerters'

    response = getAPIResponse(CNdocumentURL + subreqURL)

    # print(response)
    
    try:
        root = ET.ElementTree(ET.fromstring(response))
    except:
        print(response)

    docalerts = []
    for alert in root.findall('.//alerter'):

        alertID = alert[0].text
        alertName = alert[1].text
        
        docalerts.append((alertID, alertName))

    return docalerts  

                
def getDocumentReports(docID):
# 
    
    # First get the document dataprovider IDs
    subreqURL = 'documents/' + str(docID) + '/reports'

    response = getAPIResponse(CNdocumentURL + subreqURL)

    # print(response)
    
    try:
        root = ET.ElementTree(ET.fromstring(response))
    except:
        print(response)

    docreports = []
    for rep in root.findall('.//report'):

        repID = rep[0].text
        repName = rep[1].text
        repHasFilter = rep.attrib['hasDatafilter']
        
        docreports.append(( repID, repName, repHasFilter))

    return docreports  


def getReportSpecification(docID, reportid):
# Gets the report specification
    
    subreqURL = 'documents/' + str(docID) + '/reports/' + reportid + '/specification'

    cnts = []
    
    response = getAPIResponse(CNdocumentURL + subreqURL)

    # print(response)
    
    try:
        root = ET.ElementTree(ET.fromstring(response))
    except:
        print(response)    

    response = html.unescape(response)
    
    return response


def getDocumentDataproviders(docID):

    dataproviderlist = []
    univName = '<unknown>'
    
    subreqURL = 'documents/' + str(docID) + '/dataproviders'
    response = getAPIResponse(CNdocumentURL + subreqURL)   
    # print(subreqURL, response)
    vd_root = ET.fromstring(response)

    for dp in vd_root.findall(".//dataprovider"):
        dpID = dp.find('id').text
        dpName = dp.find('name').text
        dpType = dp.find('dataSourceType').text
        # id to universe, universe name is missing in the xml response.
        try:
            dpDSID = dp.find('dataSourceId').text
            # univName = searchRepos('universe', dpDSID)
        except:
            dpDSID = '-1'
            
        dataproviderlist.append([dpID, dpName, dpType, dpDSID])

    return dataproviderlist


def getDataObjectDetails(DOElement):
# takes as input an Eltree XML element with DataObject details,
# extracts information from it
    
    DODetail = []
    
    DOType = DOElement.tag

    objID = DOElement.find('id').text
    objName = DOElement.find('name').text
    objFormID = DOElement.find('formulaLanguageId').text
    
    #  dataprovider objects
    if DOType =='expression': 

        objDSID = DOElement.find('dataSourceObjectId').text
        objDPID = DOElement.find('dataProviderId').text
        objDPName = DOElement.find('dataProviderName').text
        objUniverse = DOElement.find('dataSourceName').text
        objDataType = DOElement.attrib['dataType']
        objQualifcation = DOElement.attrib['qualification']
        
        DODetail = ['Query Object', objID, objFormID, objName, objDataType, objQualifcation, '', objDPID, objDPName, objUniverse]

    # shared dimensions
    if DOType =='link': 

        objDSID = DOElement.find('dataSourceObjectId').text
        objDataType = DOElement.attrib['dataType']
        objQualifcation = DOElement.attrib['qualification']
        
        linkdetlinks = []
        
        for linkedObj in DOElement.findall('.//linkedExpression'):
            linkedObjID = linkedObj.attrib['id']
            linkdetlinks.append(linkedObjID)
            
        DODetail = ['Shared Dimension', objID, objFormID, objName,  objDataType, objQualifcation, linkdetlinks, '', '', '']

    # formula and grouping vars
    if DOType =='variable': 

        objDataType = DOElement.attrib['dataType']
        objQualifcation = DOElement.attrib['qualification']

        if 'grouping' in DOElement.attrib:
            groupedVar = DOElement.find('dimensionId').text
            objDef = '<Grouping of VarID ' + groupedVar + '>'
            objType = 'Group Variable'
        else:
            objDef = '\'' + DOElement.find('definition').text
            objType = 'Report Variable'
            
            
        DODetail = [objType, objID, objFormID, objName, objDataType, objQualifcation, objDef]

    # reference vars
    if DOType =='refcell': 
        
        # tags seems to be missing every now and then
        try:
            doRefObj = DOElement.find('reference').text
            doRefRep = DOElement.find('reportId').text
            doRefTxt = 'Reference to cellId <' + doRefObj + '> in reportID <'+ doRefRep + '>'
        except:
            doRefTxt = ''
        
        DODetail = ['Reference Variable', objID, objFormID, objName,  '', '', doRefTxt, '']

    return DODetail

    
def getDocumentDataObjects(docID, verbose = 0):
# Gets all details from the dataobjects (vars/dataprovider objects) in a document
    
    subreqURL = 'documents/' + docID + '/dataobjects?allInfo=true'
    response = getAPIResponse(CNdocumentURL + subreqURL)
    
    try:
        root = ET.ElementTree(ET.fromstring(response))
    except:
        print(CNdocumentURL + subreqURL, response)

    docDataObjectDetails = {}

    for el in root.getroot():

        objID = el.find('id').text
        objdet = getDataObjectDetails(el)

        docDataObjectDetails[objID] = objdet

    return docDataObjectDetails


def getDocReportIBEFilters(docID, reportID, verbose=0):

    subreqURL = 'documents/' + docID + '/reports/' + reportID + '/inputcontrols?allInfo=true'
    response = getAPIResponse(CNdocumentURL + subreqURL, 1)  

    IBEVars = []
    
    try:
        root = ET.ElementTree(ET.fromstring(response))
        
        for ic in root.findall('.//inputcontrol'):

            icName = ic.find('name').text
            
            try:
                icVar = ic.find('assignedDataObject').attrib['refId']
                IBEVars.append([icName, icVar])
            except:
                # Apperently an inputcontrol only containing groups of other input controles
                dummy = 0
            
    except:
        dummy = 0
        
        if verbose:
            print('Error in processing input controls')

    return IBEVars


def getDocumentIBEFilters(docID, verbose=0):

    # global IBE filters
    subreqURL = 'documents/' + docID + '/inputcontrols?allInfo=true'
    response = getAPIResponse(CNdocumentURL + subreqURL, 1)  

    IBEVars = []
    
    try:
        root = ET.ElementTree(ET.fromstring(response))
        
        for ic in root.findall('.//inputcontrol'):

            icName = ic.find('name').text
            
            try:
                icVar = ic.find('assignedDataObject').attrib['refId']
                IBEVars.append([icName, icVar, 'document'])
            except:
                # input control just containing groups
                dummy = 0
            
            if verbose:
                print('error 2')

    except:
        dummy = 0
        
        if verbose:
            print('error')

    
    #  report IBE filters
    docReps = getDocumentReports(docID)

    repIBE = {}
    
    for docrep in docReps:
        docrepID = docrep[0]
        docrepName = docrep[1]
        docrepHasFilter = docrep[2]

        repIBEVars = getDocReportIBEFilters(docID, docrepID)

        for var in repIBEVars:
            IBEVars.append([var[0], var[1], 'report: ' + docrepName])

    
    return IBEVars
        

def getDocReportDataFilters(docID, repID):

    subreqURL = 'documents/' + docID + '/reports/' + repID + '/datafilter'

    response = getAPIResponse(CNdocumentURL + subreqURL, 1)  

    try:
        root = ET.ElementTree(ET.fromstring(response))
    except:
        # some reports don't have a data filter,
        # this results in an error in the response.
        # I don't know yet how to find this without actually requesting the datafilter
        dummy = 0
        # print(CNdocumentURL + subreqURL, response)

    DataFilterVars = []
    
    for condition in root.findall('.//condition'):
        var = condition.attrib['key']
        DataFilterVars.append(var)

    return DataFilterVars


def getDocumentDataFilters(docID):

    docReps = getDocumentReports(docID)

    repIBE = {}
    
    for docrep in docReps:
        docrepID = docrep[0]
        docrepName = docrep[1]
        docrepHasFilter = docrep[2]

        repIBEVars = getDocReportDataFilters(docID, docrepID)
        repIBE['report: '+ docrepName] = repIBEVars

    return repIBE
    

def getAlerterUsageInReport(docID):

    docReps = getDocumentReports(docID)

    rephit = {}
    for docrep in docReps:
        docrepID = docrep[0]
        docrepName = docrep[1]        
        repspec = getReportSpecification(docID, docrepID)
  
        repalerts = re.findall(r'alertId\=\"([^"]*)\"', repspec)    

        alhits = []
        for alertlist in repalerts:
            for alert in alertlist.split(';'):
                alhits.append('alert: ' + alert)

        alhits = list(set(alhits))

        rephit['report: '+ docrepName] = alhits

    return rephit


def retrieveVarsFromText(txt):
# Takes a string as input and matches data object references
# with pattern [xx]  or [q].[xx]
    
    hitlist = []
    
    # match [query name].[var name]
    # Added whitespaces around text to match with vars at start or end of text
    # There must be some nice regex expression to fix this in a proper way...
    varhits = re.findall(r'\[[^\]]*\][\.]\[[^\]]*\]', ' ' + txt + ' ')

    for hit in varhits:
        hitlist.append(hit)
        # replace these vars with '<>' to make the next regex findall simpeler
        txt = txt.replace(hit, '<>')
    
    #  match [var name]
    varhits = re.findall(r'\[[^\]]*\]', ' ' + txt + ' ')

    for hit in varhits:
        hitlist.append(hit)

    # ontdubbelen
    hitlist = list(set(hitlist))

    return hitlist
    

def getDocElementVarDeps(docID):

    docReps = getDocumentReports(docID)

    repelhit = {}
    
    for docrep in docReps:
        docrepID = docrep[0]
        docrepName = docrep[1]
        
        subreqURL = 'documents/' + str(docID) + '/reports/' + docrepID + '/elements?allInfo=true'
    
        response = getAPIResponse(CNdocumentURL + subreqURL)

        response = html.unescape(response)
        
        hitlist = retrieveVarsFromText(response)
        
        repelhit[docrepID] = (docrepName, hitlist)    

    return repelhit
    

def getVarUsageInReports(docID):

    docReps = getDocumentReports(docID)

    rephit = {}
    for docrep in docReps:
        docrepID = docrep[0]
        docrepName = docrep[1]
        
        repspec = getReportSpecification(docID, docrepID)

        hitlist = retrieveVarsFromText(repspec)
        
        rephit[docrepID] = (docrepName, hitlist)

    return rephit


def getDocumentVarAlerterDeps(docID):

    alerters = getDocumentAlerters(docID)

    alertVars = {}
    
    for alert in alerters:

        alertID = alert[0]
        
        # First get the document dataprovider IDs
        subreqURL = 'documents/' + str(docID) + '/alerters/' + alertID
    
        response = getAPIResponse(CNdocumentURL + subreqURL)

        try:
            root = ET.ElementTree(ET.fromstring(response))
    
            docalerts = []

            varlist = []
            
            for rule in root.findall('.//rule'):

                for cond in rule.findall('.//condition'):
    
                    try:
                        condexp = cond.attrib['expressionId']
                    except:
                        condexp = '<>'

                    varlist.append(condexp)
        except:
            varlist = []

        if varlist != []:
            alertVars[alertID] = varlist

    return alertVars


def getDocDPFilterOperands(docID, dpID):
# Searches for dataprovider objects used as a filter operand
# Used for lineage in reports
    
    subreqURL = 'documents/' + str(docID) + '/dataproviders/' + str(dpID) + '/specification'

    response = getAPIResponse(CNdocumentURL + subreqURL)

    # print(response)
    
    try:
        root = ET.ElementTree(ET.fromstring(response))
    except:
        print(response)

    dpobjOperands = []
    deplist = []
    
    for operandObj in root.findall('.//operands'):

        try:
            refObj = operandObj.attrib['referencedDPObject']
            dpobjOperands.append(refObj)
        except:
            refObj = ''

    if len(dpobjOperands) > 0:
        deplist = [dpID, 'DP filter', dpobjOperands]
        
    return deplist

    
def getDocDPDependencies(docID, docVarsObjs):
# Finds relations between dataproviders (query filter based on other query objects)
    
    dps = getDocumentDataproviders(docID)

    dpobjDeps = []
    
    for dp in dps:
        # print(dp)
        dpID = dp[0]
        dpobjs = getDocDPFilterOperands(docID, dpID)

        if len(dpobjs)>0:
            for varobj in docVarsObjs:
                if docVarsObjs[varobj][6] == dpID:      
                    dpobjDeps.append([docVarsObjs[varobj][1], 'DP filter', dpobjs[2]])


    return dpobjDeps

    
def getAllVarDependencies(docID, docVarsObjs, verbose = 0):
# Gets the depencies for all kinds of data objects.
# varDepList structure: <Dependend variable>, <Dependency Type>, <Dependency list of varID's>
# docvars: (varID, varFormID, varName, varType, varQual, varDef)

    vardepsList = []

    if verbose:
        print('formula deps')

    # append variable -> variable formula dependencies 
    for var in docVarsObjs:

        # only report variables have formulas. Data objects are endpoints in lineage

        if docVarsObjs[var][0] == 'Report Variable':
            varID = docVarsObjs[var][1]
            varFormula = docVarsObjs[var][6]
           
            varFormulaHits = retrieveVarsFromText(varFormula)

            vardeps = []
            for vardep in docVarsObjs:
                vardepID = docVarsObjs[vardep][1]
                vardepFormID = docVarsObjs[vardep][2]
    
                # print(varID, varFormula, vardepFormID)

                # CCH 20251205 te grof, matcht SD VAR naam aan alle betrokken DP object namen als de SD Var naam niet gewijzigd is...
                # if varFormula.find(vardepFormID)>=0:
                #     vardeps.append(vardepID)
                for varIDHit in varFormulaHits:
                    if varIDHit == vardepFormID:
                        vardeps.append(vardepID)
                    
                        # print(vardepFormID, varFormula)

            vardepsList.append([varID, 'VF', vardeps])
    
    if verbose:
        print('grouping var deps')
    
    # append variable -> grouping variable dependencies 
    for var in docVarsObjs:

        if docVarsObjs[var][0] == 'Group Variable':
            varID = docVarsObjs[var][1]
            varFormula = docVarsObjs[var][6]
            # '<Grouping of VarID DP2d.DO1d>'
            
            vardeps = re.findall(r'VarID\s(.*)>', varFormula)
            vardepsList.append([varID, 'VG', vardeps])

    if verbose:
        print('shared dim deps')
        
    # append variable -> shared dimension dependencies
    for var in docVarsObjs:
        if docVarsObjs[var][0] == 'Shared Dimension':
            varID = docVarsObjs[var][1]
            varLinks = docVarsObjs[var][6]

            vardepsList.append([varID, 'SD', varLinks])

    if verbose:
        print('report deps')
        
    # append variable -> report dependencies
    repvars = getVarUsageInReports(docID)

    # repvars are linked by name not by ID
    # so look for ID's for given var names
    for report in repvars:
        vardeps = []

        # print('DBG',report, repvars[report])
        
        for depvar in repvars[report][1]:
            for allvar in docVarsObjs:
                if depvar == docVarsObjs[allvar][2]:
                    # print(depvar)
                    vardeps.append(docVarsObjs[allvar][1])
                
        # print('checking', vardeps)
        vardepsList.append(['report: '+ repvars[report][0], 'RP', vardeps])

    if verbose:
        print('Datafilters')
            
    # append variabele -> report IBE filter
    docDataFilters= getDocumentDataFilters(docID)

    for report in docDataFilters:
        
        vardeps = []
        for depvar in docDataFilters[report]:
            for allvar in docVarsObjs:
                if depvar == docVarsObjs[allvar][2]:
                    vardeps.append(docVarsObjs[allvar][1])
        
        # print(vardeps)                
        vardepsList.append([report, 'DF', vardeps])

    if verbose:
        print('IBE filters')

    IBEList = getDocumentIBEFilters(docID)

    for ibe in IBEList:
        vardepsList.append([ibe[2], 'IBE', [ibe[1]]])

            
    if verbose:
        print('alerters')
    
    # append variable -> alerter dependencies
    alertVars = getDocumentVarAlerterDeps(docID)

    for alert in alertVars:
        vardeps = alertVars[alert]
        # print('alert deps:', vardeps)
        vardepsList.append(['alert: ' + alert, 'AL', vardeps])

    # append alerter -> report dependencies
    alertReps = getAlerterUsageInReport(docID)
    
    for alertrep in alertReps:

        if len(alertReps[alertrep])>0:
            vardeps = alertReps[alertrep]
            # print(vardeps)
            vardepsList.append([alertrep, 'AR', vardeps])    

    if verbose:
        print('query filters')
    
    # append query object -> query filter dependencies
    dpobjDeps = getDocDPDependencies(docID, docVarsObjs)

    for dpobjDep in dpobjDeps:
        vardepsList.append(dpobjDep)

    if verbose:
        print('report elements')
    
    # append report element dependencies
    # like vars used in titles of visuals
    repelvars = getDocElementVarDeps(docID)

    for report in repelvars:  

        vardeps = []
        for depvar in repelvars[report][1]:
            for allvar in docVarsObjs:
                if depvar == docVarsObjs[allvar][2]:
                    # print(depvar)
                    vardeps.append(docVarsObjs[allvar][1])     
                    
        vardepsList.append(['report: '+ repvars[report][0], 'RPE', vardeps])
        
    return(vardepsList)


def getSingleVarDependencies(vardepsList):
# Extracts a list of variables in a dependency to indivudual lines per variable
    
    singleVarDepList = []

    for vardeps in vardepsList:

        varID = vardeps[0]
        deptype = vardeps[1]
        deplist = vardeps[2]

        for vardepID in deplist:
            singleVarDepList.append([varID, vardepID, deptype])
        
    return singleVarDepList

    
def getVarDepType(VarDeps):

    minID = -1
    minVarDep = []

    depType = 'None'
    
    for i, vardep in enumerate(VarDeps):
        # print(vardep)

        # dependencies might end in a document IBE filter, so check for 'document' as well, next to reports.
        if (vardep[2].find('report: ') >=0  or vardep[2].find('document')) >= 0:
            if vardep[3] == 1 :
                depType = 'Direct'
            else:
                if depType == 'None':
                    depType = 'Indirect'
                else:  
                    a=1   
            
    return depType


def getShortestVarDep(VarDeps):
# Gets shortest path from var to report
# When no paths lead to the report, get overall shortest path
    
    minDepth = 100
    minDepthRep = 100
    
    minID = -1
    minVarDep = ['', '', '', 0]
    minVarDepRep =  ['', '', '', 0]
    
    for i, vardep in enumerate(VarDeps):

        pathlength = vardep[3]

        if (vardep[2].find('report: ') >=0  or vardep[2].find('document')) >= 0:
            if pathlength < minDepthRep:
                minDepthRep = pathlength
                minVarDepRep = vardep
        else:
            if pathlength < minDepth:
                minDepth = pathlength
                minVarDep = vardep

    if minVarDepRep[0] != '':
        minVarDep = minVarDepRep
        
    return minVarDep
        
    
def getVarDependencyPath(VarID, varDeps, pathstring, depth=1):
# recursive function to get the dependency path of a variabele
    
    myvardep = []
    founddep = 0
    
    for vardep in varDeps:

        if VarID == vardep[1]:

            founddep = 1
            childvardeps = getVarDependencyPath(vardep[0], varDeps, pathstring + ' -> ' + vardep[0] + ' ('+ vardep[2] + ')', depth+1)

            if len(childvardeps) > 0:
                for tuple in childvardeps:
                    myvardep.append(tuple)
            else:
                myvardep.append( (vardep[1], pathstring + ' -> ' + vardep[0]  + ' ('+ vardep[2] + ')' , vardep[0], depth))
         
    return myvardep


def getDocumentDependencies(docID, verbose = 0):

    if verbose:
        print('getting document dataobjects')
        
    docAllVarsObjs = getDocumentDataObjects(docID)
    
    if verbose:
        print('getting dependencies:')

    AllVarDeps = getAllVarDependencies(docID, docAllVarsObjs, verbose)

    if verbose:
        print()
        print('getting single var deps')
    
    SingleVarDeps = getSingleVarDependencies(AllVarDeps)

    varDeps = []
    
    if verbose:
        print('getting dependency paths')
        print()

    for var in docAllVarsObjs:
        varID = docAllVarsObjs[var][1]

        pathstring = varID 
        VarDepPaths = getVarDependencyPath(varID, SingleVarDeps, pathstring, depth=1)

        ShortestVarDepPath = getShortestVarDep(VarDepPaths)
        
        depType = getVarDepType(VarDepPaths)

        varDeps.append([ varID, docAllVarsObjs[var][2], ShortestVarDepPath[1], depType])

    listObjects = DictToList(docAllVarsObjs)
    DF_docvarsobjs = pd.DataFrame(listObjects, columns =['Var Origin', 'Var ID', 'Var Ref Name', 'Var Name', 'Var Datatype', 'Var Property', 'Var Definition', 'Query ID', 'Query Name', 'Universe'])

    DF_vardeps = pd.DataFrame(varDeps, columns =['Var ID', 'Var Name', 'Dependency Path', 'Dependency Type'])


    DF_docvarsobjs = DF_docvarsobjs.sort_values("Var ID", ascending=True)
    DF_vardeps = DF_vardeps.sort_values("Var ID", ascending=True)

    # just append the two relevant dependency columns to this dataframe
    DF_merged = pd.concat([DF_docvarsobjs, DF_vardeps[DF_vardeps.columns[[2,3]]]],  axis=1)
    
    return DF_merged
