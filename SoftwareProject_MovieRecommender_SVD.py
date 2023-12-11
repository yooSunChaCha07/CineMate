import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import warnings
from IPython import get_ipython
import subprocess



warnings.filterwarnings('ignore')


# ## 1. Downloading MovieLens-100k Dataset
DATASET_LINK='http://files.grouplens.org/datasets/movielens/ml-100k.zip'

# Replace this:
# get_ipython().system('wget -nc http://files.grouplens.org/datasets/movielens/ml-100k.zip')
# get_ipython().system('unzip -n ml-100k.zip')

# With this:
# subprocess.run(['wget', '-nc', 'http://files.grouplens.org/datasets/movielens/ml-100k.zip'])
subprocess.run(['unzip', '-n', 'ml-100k.zip'])


# ## 2. Loading and Pre-Processing MovieLens Dataset

# ### Loading u.info

# > The number of users, items, and ratings in the u data set

# In[4]:


overall_stats = pd.read_csv('ml-100k/u.info', header=None)
# print("Details of users, items and ratings in the MovieLens dataset: ",list(overall_stats[0]))


# ### Loading u.data

# > The full u data set, 100000 ratings by 943 users on 1682 items.
#               Each user has rated at least 20 movies.  Users and items are
#               numbered consecutively from 1.  The data is randomly
#               ordered. This is a tab separated list of 
# 	         user id | item id | rating | timestamp. 
#               The time stamps are unix seconds since 1/1/1970 UTC 

# In[5]:


# renaming 'item id' to 'movie id'
column_names_data = ['user id', 'movie id', 'rating', 'timestamp']
df_data = pd.read_csv('ml-100k/u.data', sep='\t', header=None, names=column_names_data)
df_data.head() 


# In[6]:


len(df_data), min(df_data['movie id']), max(df_data['movie id'])


# ### Loading u.item

# > Information about the items (movies); this is a tab separated
#               list of
#               movie id | movie title | release date | video release date |
#               IMDb URL | unknown | Action | Adventure | Animation |
#               Children's | Comedy | Crime | Documentary | Drama | Fantasy |
#               Film-Noir | Horror | Musical | Mystery | Romance | Sci-Fi |
#               Thriller | War | Western |
#               The last 19 fields are the genres, a 1 indicates the movie
#               is of that genre, a 0 indicates it is not; movies can be in
#               several genres at once.
#               The movie ids are the ones used in the u.data data set.

# In[7]:


column_names_item = 'movie id | movie title | release date | video release date | IMDb URL | unknown | Action | Adventure | Animation | Children | Comedy | Crime | Documentary | Drama | Fantasy | Film-Noir | Horror | Musical | Mystery | Romance | Sci-Fi | Thriller | War | Western'
column_names_item = column_names_item.split(' | ')
column_names_item


# In[8]:


df_items = pd.read_csv('ml-100k/u.item', sep='|', header=None, names=column_names_item, encoding='latin-1')
df_items


# In[9]:


df_movies = df_items[['movie id','movie title']]
df_movies.head()


# ### Finding duplicate movie ids using grouping by movie titles

# In[10]:


len_original = len(df_items)
len_grouped = len(df_items.groupby(by='movie title'))
# print((len_original, len_grouped))
# print("Duplicate Movie IDs =", len_original - len_grouped)


# ### Merging different datasets to get final refined dataset

# In[11]:


df_merged = pd.merge(df_data, df_movies, how='inner', on='movie id')
df_merged.head()


# In[12]:


# dropping 'movie id' as it contains 18 duplicates
df_refined = df_merged.groupby(by=['user id', 'movie title'], as_index=False).agg({"rating": "mean"})
df_refined.head()


# ## 3. Performing Exploratory Data Analysis

# In[13]:


# print(df_refined.describe())


# In[14]:


num_users = len(df_refined['user id'].value_counts())
num_items = len(df_refined['movie title'].value_counts())
# print('Unique number of users in the dataset: {}'.format(num_users))
# print('Unique number of movies in the dataset: {}'.format(num_items))


# In[15]:


# Plotting movies with most ratings
# movie_rating_counts = df_refined.groupby('movie title').size().sort_values(ascending=False)
# print(movie_rating_counts.head())

# top_n_movies = movie_rating_counts.head(20)
# plt.figure(figsize=(10,5))
# top_n_movies.plot(kind='bar')
# plt.title('Top 20 movies with the most ratings')
# plt.xlabel('Movie Title')
# plt.ylabel('Number of Ratings')
# plt.xticks(rotation=90)
# plt.show()


# # In[16]:


# # Plotting genre information
# genres = column_names_item[6:]
# genre_data = df_items[genres].sum().sort_values(ascending=False)

# plt.figure(figsize=(10, 5))
# genre_data.plot(kind='bar')
# plt.title('Popularity of Movie Genres')
# plt.xlabel('Genre')
# plt.ylabel('Number of Movies')
# plt.xticks(rotation=90)
# plt.show()


# # In[17]:


# # Plotting users with most ratings
# user_rating_counts = df_refined.groupby('user id').size().sort_values(ascending=False)
# print(user_rating_counts.head())

# top_n_users = user_rating_counts.head(20)
# plt.figure(figsize=(10,5))
# top_n_users.plot(kind='bar')
# plt.title('Top 20 users with the most ratings')
# plt.xlabel('User ID')
# plt.ylabel('Number of Ratings Given')
# plt.show()


# In[18]:


df_rating_count = pd.DataFrame(df_refined.groupby(['rating']).size(), columns=['count'])
df_rating_count


# In[19]:


ax = df_rating_count.reset_index().rename(columns={'index': 'rating score'}).plot('rating', 'count', 'bar',
    figsize=(12, 6),
    title='Rating Score vs Number of Ratings')

ax.set_xlabel("Rating (1 - 5)")
ax.set_ylabel("Number of Ratings")


# ## 4. Modeling using SVD (Single Value Decomposition) / Matrix Factorization

# ### Creating lists for unique user ids and movie names

# In[20]:


# Displaying uniques users and movies
unique_users = df_refined['user id'].unique() 
unique_movies = df_refined['movie title'].unique()
len(unique_movies),len(unique_users)


# In[21]:


# Creating users & movies lists
users_list = df_refined['user id'].tolist()
movie_list = df_refined['movie title'].tolist()
len(users_list), len(movie_list)


# ### Creating a list for movie ratings

# In[22]:


ratings_list = df_refined['rating'].tolist()
# print(ratings_list)
len(ratings_list)


# ### Creating mapping for movies with index

# In[23]:


movies_dict = {unique_movies[i] : i for i in range(len(unique_movies))}
# print(movies_dict)
# print(len(movies_dict))


# ### Creating a utility matrix for the available data

# In[24]:


# Creating an empty array with rows as movies, columns as users

utility_matrix = np.asarray([[np.nan for j in range(len(unique_users))] for i in range(len(unique_movies))])
# print("Shape of the utility matrix:", utility_matrix.shape)

for i in range(len(ratings_list)):
    utility_matrix[movies_dict[movie_list[i]]][users_list[i]-1] = ratings_list[i]

utility_matrix


# In[25]:


# Normalizing the utility matrix across movies column
mask = np.isnan(utility_matrix)
masked_arr = np.ma.masked_array(utility_matrix, mask)
temp_mask = masked_arr.T
rating_means = np.mean(temp_mask, axis=0)

# Imputing nan's with mean values of ratings
filled_matrix = temp_mask.filled(rating_means)
filled_matrix = filled_matrix.T
filled_matrix = filled_matrix - rating_means.data[:,np.newaxis]


# In[26]:


filled_matrix = filled_matrix.T / np.sqrt(len(movies_dict)-1)
filled_matrix


# In[27]:


filled_matrix.shape


# In[28]:


# Computing the SVD of the input matrix
U, S, V = np.linalg.svd(filled_matrix)


# In[29]:


movies_list_lowercase = [i.lower() for i in unique_movies]


# In[30]:


# Calculating the cosine similarity (sorting by most similar and returning the top N)
def top_cosine_similarity(data, movie_id, top_n=10):
    index = movie_id 
    movie_row = data[index, :]
    magnitude = np.sqrt(np.einsum('ij, ij -> i', data, data))
    similarity = np.dot(movie_row, data.T) / (magnitude[index] * magnitude)
    sort_indexes = np.argsort(-similarity)
    # print(sort_indexes[:top_n])
    return sort_indexes[:top_n]


# In[31]:


# Getting k-principal components to represent movies (defaults to 50)       
def get_similar_movies(movie_name, top_n, k = 50):
    sliced = V.T[:, :k] # representative data
    movie_id = movies_dict[movie_name]
    indices = top_cosine_similarity(sliced, movie_id, top_n)
    # print("Indices:", indices)
    # print()
    # print("Top " + str(top_n-1) + " movies which are very much similar to - " + movie_name + " are: /n")
    # for i in indices[1:]:
    #     print(unique_movies[i])
    similar_movies = []
    for i in indices[1:]:
        similar_movies.append(unique_movies[i])
        
    return similar_movies


# ### Dynamically suggesting movie name from the existing movie corpus based on the user input

# In[32]:


# Returning movie suggestions to the user

def get_movie_suggestions(movie):
    temp = ""
    movie_suggestions = movies_list_lowercase.copy()
    for i in movie:
        suggested_output = []
        temp += i
        for j in movie_suggestions:
            if temp in j:
                suggested_output.append(j)
        if len(suggested_output) == 0:
            return movie_suggestions
        suggested_output.sort()
        movie_suggestions = suggested_output.copy()
        
    return movie_suggestions


# In[33]:


def recommender():
    
    try:
        movie_name = input("Input movie name: ")
        movie_name_lower = movie_name.lower()
        if movie_name_lower not in movies_list_lowercase:
            raise ValueError
        else:
            num_recommendations = int(input("Input number of movies to be recommended: "))
            get_similar_movies(unique_movies[movies_list_lowercase.index(movie_name_lower)], num_recommendations+1)

    except ValueError:
        possible_movies = get_movie_suggestions(movie_name_lower)

        if len(possible_movies) == len(unique_movies):
            print("Movie entered does not exist in the dataset...")
        else:
            indices = [movies_list_lowercase.index(i) for i in possible_movies]
            print("This movie name does not match with any movie in the dataset. Please select from the suggestions below:\n", [unique_movies[i] for i in indices])
            print("")
            recommender()


# In[35]:


# recommender()


# In[ ]:

# Function to filter movies by genres
def filter_movies_by_genres(df_items, favorite_genres):
    genre_columns = [genre for genre in favorite_genres if genre in df_items.columns]
    filtered_movies = df_items[df_items[genre_columns].sum(axis=1) > 0]
    return filtered_movies['movie title'].tolist()

def get_recommendations_for_movies(movies_list, top_n_per_movie):
    recommendations = []
    for movie in movies_list:
        try:
            similar_movies = get_similar_movies(movie, top_n_per_movie + 1)
            recommendations.extend(similar_movies)
        except KeyError:
            continue
    return recommendations

def get_movies_based_on_genres(favorite_genres, top_n_per_movie=5):
    genre_based_movies = filter_movies_by_genres(df_items, favorite_genres)
    raw_recommendations = get_recommendations_for_movies(genre_based_movies, top_n_per_movie)
    unique_recommendations = list(set(raw_recommendations))
    return unique_recommendations
