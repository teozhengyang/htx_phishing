import json
import tldextract
from extractor.extractor import Extractor
from image_hashing_storage import ImageHashingStorage

urls_ministries =["http://www.mci.gov.sg", "http://www.mccy.gov.sg", "http://www.mindef.gov.sg", "http://www.moe.gov.sg", 
                    "http://www.mof.gov.sg", "http://www.mfa.gov.sg", "http://www.moh.gov.sg", "http://www.mha.gov.sg", 
                    "http://www.mlaw.gov.sg", "http://www.mom.gov.sg", "http://www.mnd.gov.sg", "http://www.msf.gov.sg",
                    "http://www.mse.gov.sg", "http://www.mti.gov.sg", "http://www.mot.gov.sg", "http://www.pmo.gov.sg"
                    ]
urls_stats_boards = ["https://www.acra.gov.sg", "https://www.a-star.edu.sg", "https://www.boa.gov.sg", "https://www.bca.gov.sg",
                       "https://www.cpf.gov.sg/", "https://www.caas.gov.sg/", "https://www.csc.gov.sg/", "https://www.cccs.gov.sg/",
                       "https://www.cea.gov.sg/", "https://www.dsta.gov.sg/", "https://www.edb.gov.sg/", "https://www.ema.gov.sg/",
                       "https://www.entreprisesg.gov.sg/", "https://www.gra.gov.sg/", "https://www.tech.gov.sg/", "https://www.hpb.gov.sg/",
                       "https://www.hsa.gov.sg/", "https://www.htx.gov.sg/", "https://www.hlb.gov.sg/", "https://www.hdb.gov.sg/", 
                       "https://www.imdb.gov.sg/", "https://www.iras.gov.sg/", "https://www.ipos.gov.sg/", "https://www.jtc.gov.sg/",
                       "https://www.lsb.mlaw.gov.sg/", "https://www.lta.gov.sg/", "https://www.muis.gov.sg/", "https://www.mpa.gov.sg/",
                       "https://www.mas.gov.sg/", "https://www.nac.gov.sg/", "https://www.ncss.gov.sg/", "https://www.nea.gov.sg/",
                       "https://www.nhb.gov.sg/", "https://www.nlb.gov.sg/", "https://www.nparks.gov.sg/", "https://www.pa.gov.sg/",
                       "https://www.peb.gov.sg/", "https://www.pub.gov.sg/", "https://www.ptc.gov.sg/", "https://www.sdc.gov.sg/",
                       "https://www.seab.gov.sg/", "https://www.sfa.gov.sg/", "https://www.sla.gov.sg/", "https://www.smc.gov.sg/",
                       "https://www.snb.gov.sg/", "https://www.spc.gov.sg/", "https://www.stb.gov.sg/", "https://www.sportsingapore.gov.sg/",
                       "https://www.toteboard.gov.sg/", "https://www.tcmpb.gov.sg/", "https://www.ura.gov.sg/", "https://www.ssg-wsg.gov.sg/",
                       "https://www.yellowribbon.gov.sg/"
                       ]
urls_organs_of_state = ["https://www.agc.gov.sg/", "https://www.ago.gov.sg/", "https://www.iac.gov.sg/", "https://www.istana.gov.sg/",
                          "https://www.judiciary.gov.sg/", "https://www.parliament.gov.sg/", "https://www.psc.gov.sg/", "https://www.cabinet.gov.sg/"
                        ]
urls_others = ["https://www.google.com", "https://www.facebook.com", "https://www.instagram.com", "https://www.x.com",
                 "https://www.shopee.com", "https://www.lazada.com", "https://www.amazon.com", "https://www.ticketmaster.com",
                 "https://www.carousell.sg", "https://www.dbs.com.sg", "https://www.ocbc.com", "https://www.uob.com.sg", 
                 "https://www.citibank.com.sg", "https://www.hsbc.com.sg", "https://www.maybank.com.sg", "https://www.sc.com/sg",
                 "https://www.posb.com.sg"
                ]

def lambda_handler(event, context):
    urls = []
    all_urls_brands = []
    for url in urls:
      extractor = Extractor(url)
      result = extractor.run()
      brand = tldextract.extract(url).domain
      result = json.loads(result)
      result["Main page"]["brand"] = brand
      all_urls_brands.append(result["Main page"])
      print(result["Main page"])
      for i, login_page in enumerate(result["Login pages"]):
        result["Login pages"][i]["brand"] = brand
        all_urls_brands.append(login_page)
    with open('storage_result.json', 'w') as json_file:
        json.dump(all_urls_brands, json_file, indent=4)
    hashing_storage = ImageHashingStorage(all_urls_brands)
    hashing_storage.run()
    return {
          'statusCode': 200,
          'body': result
    }