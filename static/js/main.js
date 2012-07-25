require.config({
    paths: {
        jquery: 'libs/jquery-min',
        underscore: 'libs/underscore-min',
        backbone: 'libs/backbone-min',
        mustache: 'libs/mustache',
    },
    shim: {
        jquery: {
            exports: '$'
        },
        underscore: {
            exports: '_'
        },
        backbone: {
            deps: ['underscore', 'jquery'],
            exports: 'Backbone'
        }
    },

    // add dummy params to break caching
    urlArgs: '__nocache__=' +  (new Date()).getTime()
});

require([
    'jquery',
    'underscore',
    'backbone',
    'mustache',
    'text!/static/templates/search_bar.html.mustache',
    'text!/static/templates/ac_suggestion.html.mustache'
],
function ($, _, Backbone, Mustache, tmplSearchBar, tmplAcSuggestion) {

// the search bar
var SearchBar = Backbone.Model.extend({
    defaults: {
        query: '',

        // minimum amount of time b/w AJAX calls
        minUpdateIntervalMs: 200,
        timeoutId: null // id for the last update timeout
    },

    initialize: function () {
        this.view = new SearchBarView({model: this});
        this.acSuggestionList = new AutocompleteSuggestionList();
    },

    updateQuery: function (query) {
        if (query !== this.get('query')) {
            this.set({'query': query});

            // clear any existing update timeout
            if (this.get('timeoutId') !== null) {
                clearTimeout(this.get('timeoutId'));
            }

            // set a timeout to update once input is done coming for a bit
            var self = this;
            var timeoutId = setTimeout(function () {
                // update suggesion list and clear the timeout id
                self.acSuggestionList.updateSuggestions(query);
                self.set({'timeoutId': null});

            }, this.get('minUpdateIntervalMs'));

            // store the timeout id for the next update call
            this.set({'timeoutId': timeoutId});
        }
    }
});

var SearchBarView = Backbone.View.extend({
    template: Mustache.compile(tmplSearchBar),

    events: {
        'keyup input': 'updateQuery',
        'keydown input': 'updateQuery'
    },

    initialize: function () {
        // create the element and add it to the document
        this.setElement($(this.template({placeholder: 'search'})));
        this.$el.appendTo($('body'));

        // cache a ref to the input and focus it
        this.$input = this.$el.find('input');
        this.$input.focus();
    },

    updateQuery: function (e) {
        this.model.updateQuery(this.$input.val());
    }
});

// a single suggestion below the search bar
var AutocompleteSuggestion = Backbone.Model.extend({
    defaults: {
        provider: null,
        suggestion: ''
    }
});

// the suggestions collection below the search bar
var AutocompleteSuggestionList = Backbone.Collection.extend({
    model: AutocompleteSuggestion,
    url: '/search/autocomplete',

    initialize: function () {
        this.view = new AutocompleteSuggestionListView({
            el: $('#search-bar ul'),
            collection: this
        });
    },

    updateSuggestions: function (query) {
        var xhr = $.getJSON(this.url, {'query': query});

        // update the collection on reset
        var collection = this;
        xhr.success(function (data) {
            collection.reset(data.results);
        });
    }
});

var AutocompleteSuggestionListView = Backbone.View.extend({
    template: Mustache.compile(tmplAcSuggestion),

    initialize: function () {
        this.collection.on('reset', this.render, this);
    },

    render: function () {
        // get the suggestion list from the collection
        var suggestions = this.collection.toJSON();

        // clear out the old suggestions
        this.$el.children().remove();

        // add all the new suggestions
        _.each(suggestions, function (suggestion) {
            this.$el.append(this.template(suggestion));
        }, this);

        return this;
    },
});

// ENTRY POINT
$(function () {
    var searchBar = new SearchBar();
});

});
