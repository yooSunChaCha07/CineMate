var input = document.getElementById("movie-input");

input.addEventListener("keypress", function(event) {
  if (event.key === "Enter") {
    event.preventDefault();
    document.getElementById("button-addon").click();
  }
});

function getRecommendations() {
    var movieName = document.getElementById('movie-input').value;
    fetch('/recommend?movie=' + encodeURIComponent(movieName)) // Make sure to encode the movie name for URL
        .then(response => response.json())
        .then(data => {
            var recommendationsDiv = document.getElementById('recommendation-list');
            recommendationsDiv.innerHTML = ''; // Clear previous recommendations

            var row = document.createElement('div');
            row.className = 'row'; // Create a row for the cards

            // Handle the case where suggestions are returned
            if (data.error && data.suggestions) {
                recommendationsDiv.innerHTML = data.error + '<br>Please select from the suggestions below:<br>';
                data.suggestions.forEach(function(suggestion) {
                    recommendationsDiv.innerHTML += suggestion + '<br>';
                });
            } else if (data.error) {
                recommendationsDiv.innerHTML = data.error;
            } else {
                // Display recommendations if there are no errors
                data.forEach(function(movie) {
                    var col = document.createElement('div');
                    col.className = 'col-sm-6 col-md-4 col-lg-3 mb-3'; // Define the column sizes here

                    var card = document.createElement('div');
                    card.className = 'card h-100'; // Use h-100 to make all cards equal height

                    // Create an anchor tag for the IMDb link
                    var imdbLink = document.createElement('a');
                    imdbLink.href = movie.imdb_url;
                    imdbLink.target = '_blank'; // Opens the link in a new tab

                    // Add the movie poster
                    var img = document.createElement('img');
                    img.className = 'card-img-top';
                    img.src = movie.poster !== 'N/A' ? movie.poster : 'path/to/default/poster.jpg'; // Add a default poster if not available
                    img.alt = 'Movie Poster';
                    imdbLink.appendChild(img);
                    card.appendChild(imdbLink);

                    // Add the card body
                    var cardBody = document.createElement('div');
                    cardBody.className = 'card-body';

                    var title = document.createElement('h5');
                    title.className = 'card-title';
                    title.textContent = movie.title;
                    cardBody.appendChild(title);

                    var text = document.createElement('p');
                    text.className = 'card-text';
                    text.innerHTML = 'Director: ' + movie.director + '<br>' +
                                     'Actors: ' + movie.actors + '<br>' +
                                     'Genre: ' + movie.genre + '<br>' +
                                     'Rating: ' + movie.rating;
                    cardBody.appendChild(text);

                    // Add "Add to Favorites" button
                
                    var addButton = document.createElement('a');
                    addButton.textContent = 'Add to Favorites';
                    addButton.className = 'btn addFavBtn';
                    addButton.onclick = function() { addToFavorites(movie.title, movie.poster,movie.genre); };
                    cardBody.appendChild(addButton);


                    card.appendChild(cardBody);

                    // Append card to column and column to row
                    col.appendChild(card);
                    row.appendChild(col);
                });
                // Append row to the recommendations container
                recommendationsDiv.appendChild(row);
            }
        })
        .catch(error => {
            console.error('Error fetching recommendations:', error);
            recommendationsDiv.innerHTML = 'Failed to get recommendations.';
        });
}

function addToFavorites(movieTitle, moviePoster, movieGenres) {
    var primaryGenre = movieGenres.split(', ')[0];

    fetch('/add_to_favorites', {
        method: 'POST',
        body: JSON.stringify({
            movie_title: movieTitle,
            movie_poster: moviePoster,
            movie_genre: primaryGenre 
        }),
        headers: {
            'Content-Type': 'application/json',
            // Add CSRF token if necessary
        },
        credentials: 'include'
    })
    .then(response => response.json())
    .then(data => {
        if(data.status === 'success') {
            alert('Movie added to favorites');
        } else {
            // Alert the user if the movie is already in favorites
            alert(data.message);  // Example: 'Movie already in favorites'
        }
    })
    .catch(error => {
        console.error('Error adding movie to favorites:', error);
        alert('Error occurred while adding movie to favorites');
    });
}