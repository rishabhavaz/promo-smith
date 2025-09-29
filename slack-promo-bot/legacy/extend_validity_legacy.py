# pip install git+https://github.com/milesrichardson/ParsePy.git
import random
import os
import json
import csv

os.environ["PARSE_API_ROOT"] = "https://parseapi.back4app.com/"

from parse_rest.datatypes import Object
from parse_rest.connection import register
from parse_rest.query import QueryResourceDoesNotExist

#INS/PAR/THP/GOV/ORG/PRO/AVZ - NAME - xxxx
#ARMB/ACE/ACE1Y/ACAP/ACAPEXT/SPEXT/RZPLT/STRLT/2DA/LOANER/MGRT/LEGACY - Support Trainings
promoPrefix = "AVZ-2DA-"
duration="LIFETIME" #LIFETIME/nD/nM/nY
distributionPartner = "AVAZ"#"EYE-TECH"
#appId = 'com.avazapp.autism.en_in.avaz'


def set_and_register_repo():
    # Parse Debug Keys:
    APPLICATION_ID = '<APPLICATION_ID>'
    REST_API_KEY = '<REST_API_KEY>'
    MASTER_KEY = '<MASTER_KEY>'
    register(APPLICATION_ID, REST_API_KEY, master_key=MASTER_KEY)


def generate(unique,userId):
    userId = userId.lower().strip()
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
    set_and_register_repo()
    while True:
        value = "".join(random.choice(chars) for _ in range(4))
        if value not in unique:
            try:
                promo = PromoCodeInfo.Query.all().filter(promoCodeId=promoPrefix+value).get()
            except QueryResourceDoesNotExist:
                promo = PromoCodeInfo(promoCodeId=promoPrefix+value)
                promo.promoCodeDeviceCountLimit = 1
                promo.promoCodeUser = userId
                promo.promoCodeDuration = duration
                # promo.promoCodeStartDate = "2024-09-06T11:52:13.070701"
                # promo.promoCodeEndDate = "2025-09-06T11:52:13.070701"
                promo.promoCodeDistributionPartner = distributionPartner
                # promo.validApplicationIds = ['com.avazapp.autism.en.AvazEverydayBeta']
                promo.save()
                unique.add(value)
                print (promoPrefix+value+" for "+userId)
                break


class PromoCodeInfo(Object):
    pass

unique = set()

if __name__=='__main__':
    with open('extension.csv') as csv_file:
        csv_reader = csv.reader(csv_file)
        for row in csv_reader:
            generate(unique,row[0])

