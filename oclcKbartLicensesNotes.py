#!/usr/bin/python
# -*- coding: UTF-8 -*-

import requests
import time
import re
import string
import csv
import sys
from authliboclc import wskey
from authliboclc import user
import urllib2
import xml.etree.ElementTree as ET

#key value is wskey available from OCLC and it's associated secret requestable here: https://platform.worldcat.org/wskey
key = ''
secret = ''
#principal_id and principal_idns can be found in WMS Admin module under account info as "User ID at Source" and "Source System" respectively
principal_id = ''
principal_idns = ''
authenticating_institution_id = ''

ns = {'os' : 'http://a9.com/-/spec/opensearch/1.1/', 'df' : 'http://worldcat.org/xmlschemas/LicenseManager', 'atom' : 'http://www.w3.org/2005/Atom', 'gd' : 'http://schemas.google.com/g/2005'}
rowNumber = 1
fieldNames = ["publication_title", "print_identifier", "online_identifier", "date_first_issue_online", "num_first_vol_online", "num_first_issue_online", "date_last_issue_online", "num_last_vol_online", "num_last_issue_online", "title_url", "first_author", "title_id", "embargo_info", "coverage_depth",	"coverage_notes", "publisher_name", "location", "title_notes", "staff_notes", "vendor_id", "oclc_collection_name", "oclc_collection_id", "oclc_entry_id", "oclc_linkscheme", "oclc_number",	"ACTION"]
lastCollectionID = ''
lastData = ''

inputFile = str(raw_input('Input file name: '))

#handles OverFlowErrors that may occur. Code taken from:
maxInt = sys.maxsize
decrement = True

while decrement:
    # decrease the maxInt value by factor 10 
    # as long as the OverflowError occurs.

    decrement = False
    try:
        csv.field_size_limit(maxInt)
    except OverflowError:
        maxInt = int(maxInt/10)
        decrement = True
#reads file, creates output file, creates csv reader and writer objects and begins iterating through input file
with open(inputFile, 'rU') as tsvfile:
	with open('new.tsv', 'a+') as tsvout:
		tsvreader = csv.DictReader(tsvfile, delimiter='	')
		tsvwriter = csv.DictWriter(tsvout, fieldnames=fieldNames, delimiter='	')
		tsvwriter.writeheader()
		for row in tsvreader:
			#arrays to hold rights information
			copyRights=['Copying and Sharing rights: ']
			courseRights=['Course reserve rights: ']
			eLink=['Electronic linking: ']
			remoteAccessRights=['Remote access: ']
			distanceEducationRights=['Distance Education: ']
			titleNotesContent = []
			print('Tile number: ' + str(rowNumber))
			uniqueID = row['oclc_entry_id']
			collectionID = row['oclc_collection_id']
			if collectionID == lastCollectionID:
				print("Repeat!")
				row['title_notes'] = lastData
				tsvwriter.writerow(row)
				rowNumber += 1
				lastCollectionID = collectionID
			else:
				titleNotes = row['title_notes']
				request_url = 'https://1284.share.worldcat.org/license-manager/license/search?q=collectionId:' + collectionID	
				#authentication code	taken from OCLC documentation: https://github.com/OCLC-Developer-Network/oclc-auth-python
				my_wskey = wskey.Wskey(
					key=key,
					secret=secret,
					options=None
					)

				my_user = user.User(
					authenticating_institution_id=authenticating_institution_id,
					principal_id=principal_id,
					principal_idns=principal_idns
					)

				authorization_header = my_wskey.get_hmac_signature(
					method='GET',
					request_url=request_url,
					options={
					'user': my_user,
					'auth_params': None}
					)

				myRequest = urllib2.Request(
					url=request_url,
					data=None,
					headers={'Authorization': authorization_header}
					)
				#making API call
				try:
					time.sleep(.5)
					r = urllib2.urlopen(myRequest).read()
					root = ET.fromstring(r)
					resultCheck = root.find('os:totalResults', ns)
					#check if license data is available. If license data is not found, it rewrites the row found in the file, otherwise it begins to parse the returned XML.
					emptyCheck = resultCheck.text
					print('Results: ' + emptyCheck)
					if emptyCheck == "0":
						print('no license found')
						tsvwriter.writerow(row)
						lastCollectionID = collectionID
						rowNumber += 1
				#parsing XML returned by API
				#Finding print and digital copying rights
					else:
						entry = root.find('atom:entry', ns)
						content = entry.find('atom:content', ns)
						licenseData = content.find('df:license', ns)
						terms = licenseData.find('df:terms', ns)
						copypath = terms.findall("./df:term/[df:type='Copying_and_Sharing']/df:subTerms/df:subTerm/[df:subTermName='Methods_Supported']/df:options/", ns)
						for copyoption in copypath:
							name = copyoption.findall("./df:name", ns)
							val = copyoption.findall("./df:value", ns)
							for z in name:
								for x in val:
									if z.text == "Print_Copy":
										if x.text == "true":
											copyRights.append("Print")
									elif z.text == "Digital_Copy":
										if x.text == "true":
											copyRights.append("Digital")
				#finding scholarly sharing rights
						academicPath = terms.findall("./df:term/[df:type='Copying_and_Sharing']/df:subTerms/df:subTerm/[df:subTermName='Additional_Rights_And_Restrictions']/df:options/", ns)
						for academicOption in academicPath:
							name = academicOption.findall("./df:name", ns)
							val = academicOption.findall("./df:value", ns)
							for z in name:
								for x in val:
									if z.text == "Sharing_for_Academic_Purposes":
										if x.text == "true":
											courseRights.append("Sharing for academic purposes")
				#finding course materials rights
						coursepath = terms.findall("./df:term/[df:type='Course_Materials']/df:subTerms/df:subTerm/[df:subTermName='Methods_Supported']/df:options/", ns)
						for courseoption in coursepath:
							name = courseoption.findall("./df:name", ns)
							val = courseoption.findall("./df:value", ns)
							for z in name:
								for x in val:
									if z.text == "Electronic_Course_Materials":
										if x.text == "true":
											courseRights.append("Electronic")
										elif z.text == "Printed_Course_Reserves":
											if x.text =="true":
												courseRights.append("Printed course reserves")
				#finding electronic linking rights
						elecLinkPath = terms.findall("./df:term", ns)
						for elecLinkType in elecLinkPath:
							name = elecLinkType.findall("./df:type", ns)
							val = elecLinkType.findall("./df:termValue", ns)
							for z in name:
								for x in val:
									if z.text == "Electronic_Linking":
										if x.text == "yes":
											eLink.append('yes')
										else:
											eLink.append('no')
				#finding remote access rights
						remotePath = terms.findall("./df:term", ns)
						for remoteType in remotePath:
							name = remoteType.findall("./df:type", ns)
							val = remoteType.findall("./df:termValue", ns)
							for z in name:
								for x in val:
									if z.text == "Remote_Access":
										if x.text == "yes":
											remoteAccessRights.append('yes')
										else:
											remoteAccessRights.append('no')
				#finding distance education rights
						distancePath = terms.findall("./df:term", ns)
						for distanceType in remotePath:
							name = distanceType.findall("./df:type", ns)
							val = distanceType.findall("./df:termValue", ns)
							for z in name:
								for x in val:
									if z.text == "Distance_Education":
										if x.text == "yes":
											distanceEducationRights.append('yes')
										else:
											distanceEducationRights.append('no')
				
				#checking if the arrays contain rights information actually contain data and puts it all together
						if len(copyRights) > 1:
							titleNotesContent.append(copyRights)
						if len(courseRights) > 1:
							titleNotesContent.append(courseRights)
						if len(eLink) > 1:
							titleNotesContent.append(eLink)
						if len(remoteAccessRights) > 1:
							titleNotesContent.append(remoteAccessRights)
						if len(distanceEducationRights) > 1:
							titleNotesContent.append(distanceEducationRights)
						#turns the rights information into a string and removes array punctuation	
						titleNotesData = str(titleNotesContent)
						titleNotesData = re.sub(r']\,',';', titleNotesData)
						titleNotesData = re.sub(r'\[','', titleNotesData)
						titleNotesData = re.sub(r' \'\,','', titleNotesData)
						titleNotesData = re.sub(r'\'','', titleNotesData)
						titleNotesData = re.sub(r'\]','',titleNotesData)
						row['title_notes'] = titleNotesData
						tsvwriter.writerow(row)
						rowNumber += 1
						lastCollectionID = collectionID
						lastData = titleNotesData
						print("Following terms found: ")
						print(titleNotesContent)
				except urllib2.HTTPError, e:
					print('** ' + str(e) + ' **')
tsvfile.close
tsvout.close
#rewrites the file, removing unnecessary columns
with open ('new.tsv', 'rb') as source:
	rdr = csv.reader(source, delimiter='\t')
	with open('final.txt', 'wb') as result:
		wtr = csv.writer(result, delimiter='\t')
		for r in rdr:
			wtr.writerow((r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[10], r[11], r[12], r[13], r[14], r[15],r[16],r[17],r[18],r[19],r[20],r[21],r[23],r[24]))
source.close
result.close
