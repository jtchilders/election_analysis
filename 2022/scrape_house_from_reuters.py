#!/Users/jchilders/mconda3/2022-06-16/bin/python
from selenium import webdriver
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import pandas as pd
import time

def get_candidate_info(candidate_el):
   cand_name_el = candidate_el.find_element(By.CLASS_NAME,'cand-name')
   candidate_name = cand_name_el.text
   candidate_incumbant = False
   if '*' in candidate_name: 
      candidate_incumbant = True
      candidate_name = candidate_name.replace('*','').strip()
   candidate_winner = False
   if '✓' in candidate_name:
      candidate_name = candidate_name.replace('✓','').strip()
      candidate_winner = True
   
   cand_party_el = candidate_el.find_element(By.CLASS_NAME,'cand-party')
   cand_party = cand_party_el.text
   
   cand_votes_el = candidate_el.find_element(By.CLASS_NAME,'cand-votes')
   cand_votes = int(cand_votes_el.text.replace(',',''))

   cand_pct_el = candidate_el.find_element(By.CLASS_NAME,'cand-pct')
   try:
      cand_pct = float(cand_pct_el.text.replace('%','').replace('<',''))
   except:
      print('failed to parse: ',cand_pct_el.text)
      raise
   
   return candidate_name,candidate_incumbant,candidate_winner,cand_party,cand_votes,cand_pct

def get_percent_votes_counted(table):
   footer = table.find_element(By.TAG_NAME,'tfoot')
   column = footer.find_element(By.TAG_NAME,'td')
   text = column.text
   idx = str(text).find('%')
   pct = float(text[0:idx])
   return pct


driver = webdriver.Chrome('/Users/jchilders/mconda3/2022-06-16//lib/python3.8/site-packages/chromedriver_binary/chromedriver')

states = [
'Alabama',
'Alaska',
'Arizona',
'Arkansas',
'California',
'Colorado',
'Connecticut',
'Delaware',
'Florida',
'Georgia',
'Hawaii',
'Idaho',
'Illinois',
'Indiana',
'Iowa',
'Kansas',
'Kentucky',
'Louisiana',
'Maine',
'Maryland',
'Massachusetts',
'Michigan',
'Minnesota',
'Mississippi',
'Missouri',
'Montana',
'Nebraska',
'Nevada',
'New Hampshire',
'New Jersey',
'New Mexico',
'New York',
'North Carolina',
'North Dakota',
'Ohio',
'Oklahoma',
'Oregon',
'Pennsylvania',
'Rhode Island',
'South Carolina',
'South Dakota',
'Tennessee',
'Texas',
'Utah',
'Vermont',
'Virginia',
'Washington',
'West Virginia',
'Wisconsin',
'Wyoming',
]
url = 'https://www.reuters.com/graphics/USA-ELECTION/RESULTS/dwvkdgzdqpm/{0}/'


us_house_rows = []
us_senate_rows = []
for state in states:
   print('processing state: ',state)
   driver.get(url.format(state.lower().replace(' ','-')))
   time.sleep(3)

   # US Senate Results
   try:
      els = driver.find_element(By.CLASS_NAME,'senate')
      # get results tables for each district
      tables = els.find_elements(By.CLASS_NAME,'state-table-results')
      if len(tables) == 1:
         table = tables[0]
         candidates_el = table.find_elements(By.CLASS_NAME,'candidate')

         pct_votes_counted = get_percent_votes_counted(table)

         for candidate_el in candidates_el:
            name,incum,win,party,votes,pct = get_candidate_info(candidate_el)


            row_entry = {
               'state': state,
               'candidate_name': name,
               'candidate_incumbant': incum,
               'candidate_winner': win,
               'candidate_party': party,
               'candidate_votes': votes,
               'candidate_pct': pct,
               'distrcit_pct_reporting': pct_votes_counted,
               'race':'senate',
            }
            print(row_entry)
            us_senate_rows.append(row_entry)
   except NoSuchElementException:
      print(state,' has no senate results')


   # US House Results

   # move into House results
   els = driver.find_element(By.CLASS_NAME,'house')
   
   # get results tables for each district
   tables = els.find_elements(By.CLASS_NAME,'state-table-results')

   for table in tables:

      dist_name_el = table.find_element(By.CLASS_NAME,'district-name')
      district_name = dist_name_el.text
      print(district_name)

      candidates_el = table.find_elements(By.CLASS_NAME,'candidate')

      pct_votes_counted = get_percent_votes_counted(table)

      for candidate_el in candidates_el:
         name,incum,win,party,votes,pct = get_candidate_info(candidate_el)


         row_entry = {
            'state': state,
            'district_name': district_name,
            'candidate_name': name,
            'candidate_incumbant': incum,
            'candidate_winner': win,
            'candidate_party': party,
            'candidate_votes': votes,
            'candidate_pct': pct,
            'distrcit_pct_reporting': pct_votes_counted,
            'race':'house',
         }
         print(row_entry)
         us_house_rows.append(row_entry)


us_house_df = pd.DataFrame(us_house_rows)
us_house_df.to_csv('2022_US_House_results.csv')

<<<<<<< HEAD:2022/scrape_house_from_routers.py
us_senate_df = pd.DataFrame(us_senate_rows)
us_senate_df.to_csv('2022_US_Senate_results.csv')
=======
df.to_csv('2022_US_House_results.csv')
>>>>>>> 5cdcb7e3e09bd0c56a9c2f53d53d49be37d4ffbf:2022/scrape_house_from_reuters.py
