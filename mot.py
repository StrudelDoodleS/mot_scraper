import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from typing import List, Dict
import numpy as np
from io import StringIO

BASE_URL = "https://www.gov.uk/guidance/mot-inspection-manual-for-private-passenger-and-light-commercial-vehicles"


def get_section_urls(url: str = BASE_URL) -> List[str]:
    """
    Retrieve section URLs from the MOT inspection manual base page.

    Args:
        url (str): The base URL of the MOT inspection manual. Defaults to BASE_URL.

    Returns:
        List[str]: A list of URLs for each section in the manual.
    """
    base_html = requests.get(url).text
    base_soup = BeautifulSoup(base_html, "html.parser")
    all_links = base_soup.find_all("li", class_="gem-c-document-list__item")
    links = [
        "/".join([BASE_URL, link.div.a["href"].split("/")[-1]])
        for link in all_links
        if link.div.text.strip()[0].isdigit()
    ]

    return links


def get_dropdowns(url: str) -> List[BeautifulSoup]:
    """
    Retrieve dropdown sections from a given MOT inspection manual section page.

    Args:
        url (str): The URL of a specific section in the MOT inspection manual.

    Returns:
        List[BeautifulSoup]: A list of BeautifulSoup objects representing each dropdown section.
    """
    html = requests.get(url).text
    soup = BeautifulSoup(html, "html.parser")
    return soup.find_all("div", class_="govuk-accordion__section")


def find_heading(tag_list, re_pattern, parent_heading):
    """
    Parent section number is bascially the regex pattern minus 1.
    Reason for this is we can end up finding sections where the parent section is not associated with 
        the desried h3/h4 etc section

        Example is 1.2. When finding a parent h3 we will find 
    """
    pattern = re.compile(re_pattern)
    
    headings = []
    numbers = []
    for item in tag_list:
        if parent_heading not in item.text.split(' ')[0]:
            continue
        match = re.search(pattern,item.text)
        if match:
            num = int(''.join(match.group().split('.')))
            headings.append(item)
            numbers.append(num)
    try:
        # max_num = np.max(numbers)
        index = np.argmax(numbers)
        
        # max)num is not useful!
        # go to headings index. pull out the text object i.e .text.split(' ')[0]
        return headings[index].text.strip()
        
    except ValueError:  
        return None


def split_and_prepend_defects(text):
    # Find the first set of parentheses and set it as the main defect descriptor
    first_paren_match = re.match(r'^(.*?)(?=\(\s*[a-z]+\))', text)
    if first_paren_match:
        main_defect = first_paren_match.group(0).strip()
    else:
        main_defect = text

    # Initialize storage for the sections
    sections = []
    start_idx = 0  # Starting index for section text

    # Pattern to find lowercase Roman numerals in parentheses
    pattern = re.compile(r'(?=\(\s*[ivxlcdm]+\))')  # Only capture sections with lowercase Roman numerals

    # Loop through matches of the pattern in the text
    for match in pattern.finditer(text):
        # Capture each section from start_idx up to the start of the match
        section = text[start_idx:match.start()].strip()
        if section:
            sections.append(f"{main_defect} {section}".strip())
        # Update start_idx to begin after this match for the next section
        start_idx = match.start()
    
    # Capture the final section after the last match
    final_section = text[start_idx:].strip()
    if final_section:
        sections.append(f"{main_defect} {final_section}".strip())
    
    # Remove the main defect prefix from the first section if it’s not split by any Roman numerals
    if len(sections) > 1:
        main_defect_text = sections.pop(0)  # Remove the first element as the main defect
        sections = [f"{main_defect_text} {section}" for section in sections]  # Prepend to each remaining section
    
    return sections

def extract_parentheses(text):
        # Find the first set of parentheses
        first_match = re.search(r'\([^()]*\)', text)
        matches = []
    
        # Add the first match if found
        if first_match:
            matches.append(first_match.group(0))
            start_idx = first_match.end()  # Update the starting index for the next search
    
            # Find subsequent parentheses with Roman numerals
            roman_matches = re.findall(r'\(\s*[ivxlcdm]+\s*\)', text[start_idx:])
            matches.extend(roman_matches)
        
        return " ".join(matches)

def gen_mot_pandas(dropdowns):

    
    h3_pattern = r"^(\d+\.[0-9]+\.[0-9]+)"
    h4_pattern = r'^(\d+\.[0-9]+\.[0-9]+\.[0-9])'
    df_list = []
    
    for idx, sub_section in enumerate(dropdowns):

        tables = sub_section.find_all("table")
        
        
        for table in tables:

            #This will skip headers that are not what we want
            #example is in 3.3 there are two tables 1 is bs we dont want.
            all_th = table.find_all('th')
            to_skip = [th.text in ['Defect','Category'] for th in all_th]
            if sum(to_skip) < len(to_skip):
                continue
            
            
            h1 = table.find_previous("h1") or table.find_previous(class_="manual-title")
            h1_heading = h1.text.strip()
            h1_mumber = int(h1_heading.split(' ')[0].rstrip('.'))
            
            h2 = table.find_previous("h2")
            h2_heading = h2.text.strip()
            h2_mumber = int(h2_heading.split(' ')[0].rstrip('.').split('.')[-1])
            #Sometimes tables are not below the initial h3 or 4
            all_h3 = table.find_all_previous('h3')
            
            
            h3 = None
            h4 = None
            
            h3_heading = find_heading(all_h3, h3_pattern, h2_heading.split(' ')[0])

            if h3_heading:
                h3_sections = h3_heading.split(' ')[0].rstrip('.').split('.')
                # Check if there are enough parts in h3_sections before accessing them
                
                if len(h3_sections) > 1:
                    all_h4 = table.find_all_previous('h4')
                    h4_heading = find_heading(all_h4, h4_pattern, h3_heading.split(' ')[0])
                    if int(h3_sections[-2]) == h2_mumber:
                        h3 = '.'.join(h3_sections)
                    else:
                        h3 = None
            
                    if h4_heading:
                        h4_sections = h4_heading.split(' ')[0].rstrip('.').split('.')
                        
                        # Check lengths to avoid IndexError
                        if (int(h4_sections[-2]) == int(h3_sections[-1])) and (int(h3_sections[-2]) == h2_mumber):
                            h4 = '.'.join(h4_sections)
                        else:
                            h4 = None


            # pandas requires it to be stringio
            df = pd.read_html(StringIO(str(table)))[0]
            df = df[~df.Defect.str.contains('Not in use')]
            
            df['Defect'] = df.Defect.apply(split_and_prepend_defects)
            
            allowed_values = {'Major','Minor', 'Dangerous'}
            df['Category'] = df.Category.str.split(' ').apply(lambda x: [item for item in x if item in allowed_values])
            
            df = df.explode(['Defect','Category']).reset_index(drop=True)
            df['section_name'] = ' '.join(h1_heading.split(' ')[1:])
            df['section_number'] = h1_mumber
            df['sub_section_name'] = ' '.join(h2_heading.split(' ')[1:])
            df['sub_section_number'] = h2_mumber
            
            if h3:
                df['topic_name'] = ' '.join(h3_heading.split(' ')[1:])
                df['topic_number'] = int(h3_sections[-1])
            if h4:
                df['sub_topic_name'] = ' '.join(h4_heading.split(' ')[1:])
                df['sub_topic_number'] = int(h4_sections[-1])
    
            df['point'] = df.Defect.apply(extract_parentheses)

            # Initialize `full_reference_code` based on available headings
            if h3 and h4:
                # Both `h3` and `h4` are available
                df['full_reference_code'] = (
                    df['section_number'].astype(str) + "." + 
                    df['sub_section_number'].astype(str) + "." + 
                    df['topic_number'].astype(str) + "." + 
                    df['sub_topic_number'].astype(str) + " " + 
                    df['point']
                )
            elif h3:
                # Only `h3` is available
                df['full_reference_code'] = (
                    df['section_number'].astype(str) + "." + 
                    df['sub_section_number'].astype(str) + "." + 
                    df['topic_number'].astype(str) + " " + 
                    df['point']
                )
            else:
                # Only section and sub-section numbers are available
                df['full_reference_code'] = (
                    df['section_number'].astype(str) + "." + 
                    df['sub_section_number'].astype(str) + " " + 
                    df['point']
                )
            df_list.append(df)
    concat_df = pd.concat(df_list).reset_index(drop=True)
    return concat_df

def generate_mot_table(dropdowns: List[BeautifulSoup]) -> pd.DataFrame:
    """
    DEPRECATED... Actually not but this doesn;t work
    I learned a valuable lessons that trying to parse every section in a custom manner through direct
        manipulation of HTML cells that are kinda wacky generates too many edge cases.
    As a result I am leaving this here as a reminger to myself... Trying a simpler approach with a data processing library like pandas
        is not a skill issue... There is a reason this library exists dag nabbit
    """
    sub_section_dfs: Dict[int, List[pd.DataFrame]] = {}
    # Comprehensive regex pattern for flexible section matching across various formats (e.g., "5.3 (a) (ii)", "10.2")
    section_pattern = re.compile(r"^(\d+\.[0-9]+(\.[0-9])?)")

    for idx, sub_section in enumerate(dropdowns):
        tables = sub_section.find_all("table")
        sub_section_dfs[idx + 1] = []

        for table in tables:
            # Find appropriate section heading and filter out irrelevant headings
            h1 = table.find_previous("h1")
            h2 = table.find_previous("h2")
            h3 = table.find_previous("h3")
            
            # Use h2/h3 based on section structure, but skip "Not in use" and irrelevant content
            section_heading = h2 if h2 and section_pattern.match(h2.text) else h3
            if not section_heading or "Not in use" in section_heading.text or "Navigation" in section_heading.text:
                continue  # Skip irrelevant sections
            
            # Extract headings and section ID for full reference code
            h3_name = section_heading.text.strip() if section_heading else ""
            h1_name = h1.text.strip() if h1 else ""
            h2_name = h2.text.strip() if h2 else ""
            section_id = section_heading["id"].replace("section-", "").replace("-", ".") if section_heading and section_heading.get("id") else ""

            # Define columns and prepare rows with consistent full reference code formatting
            columns = ["section_name", "subsection_name", "component_name", "full_reference_code"]
            columns += [th.text.strip() for th in table.find_all("th")]
            rows = []

            for tr in table.find_all("tr")[1:]:
                if tr.find_previous("th").text not in ["Category", "Defect"]:
                    continue
                cells = tr.find_all("td")
                if len(cells) == 2:
                    defect_cell = cells[0]
                    category_cell = cells[1]
                    categories = category_cell.get_text(separator="|||", strip=True).split("|||")
                    category = categories[0].strip()
                    main_text = defect_cell.get_text(separator="|||", strip=True)
                    parts = main_text.split("|||")

                    # Handle entries to format as "5.3 (a) (ii)"
                    if len(parts) > 1:
                        main_code = parts[0].split()[0].strip("()")
                        parent_desc = parts[0].split(")", 1)[1].strip().rstrip(":")
                        for i, part in enumerate(parts[1:]):
                            if part.strip() and "(" in part and ")" in part:
                                sub_code = part[part.find("(") + 1 : part.find(")")]
                                full_ref_code = f"{section_id} ({main_code}) ({sub_code})"
                                
                                sub_desc = part[part.find(")") + 1 :].strip()
                                full_desc = f"({main_code}) ({sub_code}) {parent_desc} - {sub_desc}"
                                sub_category = categories[i] if i < len(categories) else categories[0]
                                rows.append([h1_name, h2_name, h3_name, full_ref_code, full_desc, sub_category.strip()])
                    else:
                        defect_code = defect_cell.text.strip().split()[0].strip("()")
                        full_ref_code = f"{section_id} ({defect_code})"
                        rows.append([h1_name, h2_name, h3_name, full_ref_code, defect_cell.text.strip(), category])

            if rows:
                df = pd.DataFrame(rows, columns=columns)
                sub_section_dfs[idx + 1].append(df)

        if sub_section_dfs[idx + 1]:
            sub_section_dfs[idx + 1] = pd.concat(sub_section_dfs[idx + 1], ignore_index=True)
            
    final_df = pd.concat([v for v in sub_section_dfs.values() if len(v) > 0], ignore_index=True)

    final_df['section_number'] = final_df.section_name.str.split('.').str[0].str.rstrip('.')
    final_df['section_name'] = final_df.section_name.str.split(' ').str[1:].str.join(' ')
    
    final_df['subsection_number'] = final_df.subsection_name.str.split(' ').str[0].str.rstrip('.').str[-1]
    final_df['subsection_name'] = final_df.subsection_name.str.split(' ').str[1:].str.join(' ')
    
    final_df['component_number'] = final_df.component_name.str.split(' ').str[0].str.rstrip('.').str[-1]
    final_df['component_name'] = final_df.component_name.str.split(' ').str[1:].str.join(' ')

    final_df['type_ref'] = final_df['Defect'].str.split(' ').str[0].str.strip('()')
    final_df['sub_type_ref'] = np.where(final_df.full_reference_code.str.split(' ').apply(len).eq(3), final_df.full_reference_code.str.split(' ').str[-1].str.strip('()'),"")
    col_order = ['section_name','section_number','subsection_name','subsection_number','component_name','component_number','type_ref','sub_type_ref','full_reference_code','Defect','Category'] 
    return final_df[col_order]
