#!/usr/bin/env python

import sys
import re
import requests
import scraperwiki
import sys
import codecs

sys.stdout = codecs.getwriter('utf8')(sys.stdout)
api_url = 'http://en.wikipedia.org/w/api.php?action=query&format=json' 

def clear_db():
    scraperwiki.sql.execute("drop table if exists swdata;")
    scraperwiki.sql.commit()

def clean_data(data):
    data = re.sub(' ', '', data)
    data = re.sub('^\|', '', data)
    # square brackets
    data = re.sub('(\[\[)|(\]\])', '', data)
    # Anything in HTML tags
    data = re.sub('<[^<]+?>', ' ', data) 
    return data

def scrape_members(category, include_subcat='f'):
    clear_db()
    def get_data_list(members, category):
        data_list = []
        pages = []
        subcategories = []
        for member in members:
            if 'Category:' in member['title']:
                if include_subcat == 't':
                    subcategories.append(member['title'])
            else:
                pages.append(member['pageid']) 
        for page in pages:
            data = scrape_infobox(page)
            
            if data != None and len(data) > 0:
                data_list.append(data)

        print 'Scraped %s of %s pages in %s' % (len(data_list), len(pages), category)
        for subcategory in subcategories:
            scrape_members(subcategory.replace('Category:', '')) 
        return data_list

    category = category.replace(' ', '_')
    query = '&list=categorymembers&cmtitle=Category:%s&cmsort=timestamp&cmdir=desc&cmlimit=max' % category
    request = requests.get(api_url + query)
    json_content = request.json()
    members = json_content['query']['categorymembers'] 
    data_list = get_data_list(members, category)
    if len(data_list) > 0:
        scraperwiki.sql.save(['id'], data_list)

def scrape_infobox(pageid):
    query = '&action=query&pageids=%s&prop=revisions&rvprop=content' % pageid
    request = requests.get(api_url + query)
    json_content = request.json()
    pageid = json_content['query']['pages'].keys()[0]
    content = json_content['query']['pages'][pageid]['revisions'][0]['*']
    article_name = json_content['query']['pages'][pageid]['title']    

    content = re.sub('<!--[\\S\\s]*?-->', ' ', content)    

    box_occurences = re.split('{{[a-z]+box[^\n}]*\n', content.lower()) 

    if len(box_occurences) < 2:
        return None

    data = {}

    for box_occurence in box_occurences[1:]:

        infobox_end = re.search('\n[^\n{]*\}\}[^\n{]*\n', box_occurence)

        if infobox_end == None:
            return None

        box_occurence = box_occurence[:infobox_end.start():]
        box_occurence = re.split('\n[^|\n]*\|', box_occurence)

        for item in box_occurence:
            item = clean_data(item)
            if '=' in item:
                pair = item.split('=', 1)
                field = pair[0].strip()
                value = pair[1].strip()
                data[field.lower()] = value
                data['id'] = pageid
                data['article_name'] = article_name

    return data

def main():  
    scrape_members(sys.argv[1][:-1], sys.argv[1][-1])

if __name__ == '__main__':
    main()

