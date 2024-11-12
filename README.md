# MOT Scraping

This repo contains coded for scraping tables from the uk goverment website for MOT data found [here](https://www.gov.uk/guidance/mot-inspection-manual-for-private-passenger-and-light-commercial-vehicles). Note that this is only for class 3, 4, 5 & 7 vehicles, however this is the going to be most road-going vehicles

The main branch will show you a demo as well as code to generate the data. But for ease of use i reccomend using the data branch and cloning that.

# TODO

So far this repo only scrapes the 2018 MOT manual. That is good enough for most purposes. However, for more historical data needs this becmoes more challenging. Older MOT manulas (pre-2018) are in a pdf format with different layouts. Currently weighing up options of using tesseract or some kind of multi modal model to extract the reference codes.

Older manual also do not contain "Category" values (the severity of a defect). The way around this is to create a mapping from an odler manual to the 2018 manual. For example, section 0 in the 2018 manual is about number plates and VIN's. However in 2011 it is actually part of section 6.3 with slightly different points. There is a ton of overlap obviously so creating a mapping and using some kind of NLP (may not need an LLM for this, seems overkill) is in order to coreectly estimate if it is Minor, Major or Dangerous. 
