# -*- coding: utf-8 -*-
"""
Created on Tue May 11 20:23:45 2021

@author: Josh
"""

## IMPORTS

import numpy
import pandas
import sys
import re
import matplotlib

## README 
'''
Prerequirement: Create a folder called Data and put it in the same folder as this script. Download the 2019 results csv ("HoC-GE2019-results-by-constituency-csv HoC-GE2019-results-by-constituency-csv (126 KB, Excel Spreadsheet)(126 KB, Excel Spreadsheet)" from the Commons Library and place it in the Data folder: https://commonslibrary.parliament.uk/research-briefings/cbp-8749/ 
'''

'''
Steps:
    1. Read in 2019 results to a raw numpy array
    2. Construct a normal distrubution of 650 ways to redistribute LibDem vote share, 
        around 20% do not transfer
        around 48% transfer to Labour
        around 32% transfer to Conservatives 
    3. Zip this redistribution together with the 2019 results. Compare number of seats before and after to see how seats would change.
    4. Convert to voter percentage array
    5. Run this simulation 1000 times, find the average seat numbers 
'''

# Functions

def get_redistribution_matrix(average_to_labour, average_to_conservative, average_to_dnv):
    # Create Dirichlet Distribution
    seats = 650
    redistribution_matrix = numpy.random.dirichlet((average_to_labour, average_to_conservative, average_to_dnv), size=seats)
    
    redistribution_matrix_df = pandas.DataFrame(redistribution_matrix, columns=['to_lab_share', 'to_con_share', 'to_dnv_share'])
    redistribution_matrix_df = redistribution_matrix_df.rename_axis('seat')
    
    #redistribution_matrix_df[['to_con_share']].plot(kind='hist',bins=[0,0.2,0.4,0.6,0.8,1],rwidth=0.8)
    #matplotlib.pyplot.hist(redistribution_matrix_df, bins=numpy.linspace(0,1,11))
    #matplotlib.pyplot.show
    
    return redistribution_matrix_df

def read_csv_into_dataframe(raw_results_path, dtype_dic):
    raw_results = pandas.io.parsers.read_csv(raw_results_path, dtype = dtype_dic)#.values
    raw_results = raw_results.rename_axis('seat')
    return raw_results

# Determine new results after redistributing the libdem vote share from the 2019 results using the distribution share matrix
def get_new_results(raw_results, redistribution_matrix_df, parties):
    new_results = pandas.concat([raw_results, redistribution_matrix_df], axis=1)

    for party in parties:
        if party == "ld":
            new_results["new_" + party] = 0
        elif party == "con" or party == "lab":
            new_results["new_" + party] = new_results[party] + (new_results["ld"] * new_results["to_" + party + "_share"])
        else:
            new_results["new_" + party] = new_results[party]
    
    new_results["new_valid_votes"] = new_results["valid_votes"] - (new_results["to_dnv_share"] * new_results["ld"])
    
    return new_results

def get_old_results_shares(current_results, parties):
    
    for party in parties:
        current_results[party + "_share"] = current_results[party] / current_results["valid_votes"]
        
    return current_results

def get_new_results_shares(current_new_results, parties):
    
    for party in parties:
        current_new_results["new_" + party + "_share"] = current_new_results["new_" + party] / current_new_results["new_valid_votes"]
        
    return current_new_results

def capitalise_column(dataframe, column_name):
    dataframe[column_name] = dataframe[column_name].str.upper()
    
    return dataframe

def get_new_results_winners(current_new_results, parties):
    
    current_new_results = capitalise_column(current_new_results, "first_party")
    
    columns = ["new_" + party + "_share" for party in parties]
    
    current_new_results["new_first_party"] = current_new_results[columns].idxmax(axis=1).str.replace("new_", "").str.replace("_share", "").str.upper()
    
    current_new_results['changed'] = numpy.where(current_new_results['first_party'] != current_new_results['new_first_party'], 'TRUE', 'FALSE')
    
    return current_new_results
    

def determine_new_average_addition_results(current_new_results, current_average_results, parties):
    for party in parties:
        if "new_" + party + "_share" not in current_average_results.columns:
            current_average_results["new_" + party + "_share"] = 0
        
        current_average_results["new_" + party + "_share"] = current_average_results["new_" + party + "_share"] + current_new_results["new_" + party + "_share"]
        
    return current_average_results
    
def determine_new_average_results(dataframe, iterations, parties):
    for party in parties:
        dataframe["new_" + party + "_share"] = dataframe["new_" + party + "_share"] / iterations
        
    return dataframe
    
def normalise_average_results(dataframe, parties):
    # Assuming same lines from your example
    columns = ["new_" + party + "_share" for party in parties]
    dataframe[columns] = dataframe[columns].apply(lambda x: x / x.sum())
    
    return dataframe

def get_old_swing_needed(dataframe, parties):
    
    columns = [party + "_share" for party in parties]
    first_party_shares = dataframe[columns].apply(lambda row: row.nlargest(2).values[0],axis=1)
    second_party_shares = dataframe[columns].apply(lambda row: row.nlargest(2).values[-1],axis=1)
    swing_needed = first_party_shares - second_party_shares
    dataframe["swing_needed"] = swing_needed
    
    return dataframe


def get_new_swing_needed(dataframe, parties):
    
    columns = ["new_" + party + "_share" for party in parties]
    first_party_shares = dataframe[columns].apply(lambda row: row.nlargest(2).values[0],axis=1)
    second_party_shares = dataframe[columns].apply(lambda row: row.nlargest(2).values[-1],axis=1)
    swing_needed = first_party_shares - second_party_shares
    dataframe["new_swing_needed"] = swing_needed
    
    return dataframe
    
#=================================================#

# Config
numpy.set_printoptions(threshold=sys.maxsize)

pandas.set_option('display.max_rows', sys.maxsize)
pandas.set_option('display.max_columns', sys.maxsize)
pandas.set_option('display.width', sys.maxsize)

# Variables
parties = ["con", "lab", "ld", "brexit", "green", "snp", "pc", "dup", "sf", "sdlp", "uup", "alliance", "other"]

raw_results_path = 'Data/HoC-GE2019-results-by-constituency-csv.csv'
output_path = 'Data/results.csv'
dtype_dic = {party: int for party in parties}

iterations = 10000

average_to_labour = 0.514921161
average_to_conservative = 0.29652857
average_to_dnv = 0.188550269


## STEP 1
raw_results = read_csv_into_dataframe(raw_results_path, dtype_dic)

average_results = raw_results.copy(deep = True)

average_results = get_old_results_shares(average_results, parties)
average_results = get_old_swing_needed(average_results, parties)

for i in range(0, iterations):

    ## STEP 2
    redistribution_matrix_df = get_redistribution_matrix(average_to_labour, average_to_conservative, average_to_dnv)
    
    ## STEP 3 zip distribution into 2019 results, redistribute votes into new results
    new_results = get_new_results(raw_results, redistribution_matrix_df, parties)
    
    ## STEP 4 calculate vote shares for each constituency
    new_results = get_new_results_shares(new_results, parties)
   
    ## STEP 5 zip into average
    average_results = determine_new_average_addition_results(new_results, average_results, parties)

## STEP 6 perform division part of averaging
average_results = determine_new_average_results(average_results, iterations , parties)
    
## STEP 7 determine constituency winner
average_results = get_new_results_winners(average_results, parties)

##STEP 8 determine new swing needed 
average_results = get_new_swing_needed(average_results, parties)

## STEP 9 output to csv
average_results.to_csv(output_path)

print("Computation complete")