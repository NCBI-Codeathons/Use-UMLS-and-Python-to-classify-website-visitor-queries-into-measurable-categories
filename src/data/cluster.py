import pandas as pd
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import collections
import copy

quiry_df = pd.read_excel("SiteSearch2019-01-uniquesForStep2.xlsx")
n_freq = 200
n_bucket = 10
pair = []
whole_list = []
bucket_init = [[]  for i in range(n_bucket)]
bucket = bucket_init
#bucket = [[],[], [], [], []]#[[]]*n_bucket
print("bucket = ", bucket)

for i_comp1 in range(2000):
    comp1 = quiry_df['adjustedQueryTerm'][i_comp1]
    for i_comp2 in range(i_comp1+1, 2000):
        comp2 = quiry_df['adjustedQueryTerm'][i_comp2]
        score = fuzz.ratio(comp1, comp2)
        if (score > 75):
            whole_list.extend((i_comp1, i_comp2))
            pair.append((i_comp1,i_comp2))
print("whole pair = ", pair)
whole_counter =  collections.Counter(whole_list)
whole_key = whole_counter.most_common(n_freq)
print(whole_key)
i_end = 0
i_cur = 0
i = 0
range_check = 0
for key, value in (whole_key):
    key_in_pre = False
# check whether key in previous bucket
    for j_check in range(max(range_check, i_end)):
        if key in bucket[j_check]:
            key_in_pre = key in bucket[j_check]
            i_cur = j_check
    if (i_end == 0 and (bucket[0] == [])):
        i = 0
        range_check = 1
    elif ((key_in_pre)):
        i = i_cur
    elif (key_in_pre and i_end != 0):
        i = i_cur
    elif ((~key_in_pre) and (i_end < n_bucket)) :
        i_end = i_end + 1
        i = i_end
    else:
        i = 100
# end check whether key in previous bucket        

#    print("i = " , i)   
    pair_copy = pair.copy()
    if (i < n_bucket):
      for i_pair in pair_copy:
        if(key == i_pair[0]):
            bucket[i].extend(i_pair)
            index = pair.index((key, i_pair[1]))
            pair.pop(index)            
        elif(key == i_pair[1]):          
            bucket[i].extend(i_pair)


print( "set ", set(bucket[0]), set(bucket[1]), set(bucket[2]))
for ii in range(n_bucket):
    print("bucket ", ii, " = ", [quiry_df['adjustedQueryTerm'][i_name] for i_name in set(bucket[ii])])
