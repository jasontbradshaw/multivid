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
        acSuggestionList: null,

        // minimum amount of time between AJAX calls
        minUpdateIntervalMs: 200,
        timeoutId: null // id for the last update timeout
    },

    updateSuggestions: function () {
        // clear any existing update timeout
        if (this.get('timeoutId') !== null) {
            clearTimeout(this.get('timeoutId'));
        }

        // set a timeout to update once input is done coming for a bit
        var timeoutId = setTimeout(_.bind(function () {
            // update suggestion list and clear the timeout id
            this.get('acSuggestionList').updateSuggestions(this.get('query'));
            this.set({'timeoutId': null});

        }, this), this.get('minUpdateIntervalMs'));

        // store the timeout id for the next update call
        this.set({'timeoutId': timeoutId});
    }
});

var SearchBarView = Backbone.View.extend({
    template: Mustache.compile(tmplSearchBar),

    events: {
        'keyup input': 'inputUpdate',
        'keydown input': 'inputUpdate'
    },

    defaults: {
        model: null
    },

    initialize: function () {
        // create the element and add it to the document
        this.setElement($(this.template()));
        this.$el.appendTo($('body'));

        // cache a ref to the input and focus it
        this.$input = this.$el.find('input');
        this.$input.focus();

        // update the input if the query changes
        this.model.on('change:query', this.mirrorQuery, this);
    },

    inputUpdate: function () {
        // update the model's query value and suggest more options
        this.model.set({query: this.$input.val()});
        this.model.updateSuggestions();
    },

    mirrorQuery: function () {
        // copy the model's query option into the input if not focused
        if (!this.$input.is(':focus')) {
            this.$input.val(this.model.get('query'));
        }
        this.$input.focus();
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

    updateSuggestions: function (query) {
        var xhr = $.getJSON(this.url, {'query': query});

        // update the collection on reset
        xhr.success(_.bind(function (data) {
            this.reset(data.results);
        }, this));
    }
});

var AutocompleteSuggestionListView = Backbone.View.extend({
    template: Mustache.compile(tmplAcSuggestion),

    events: {
        'click li': 'clickSuggestion'
    },

    defaults: {
        collection: null, // the AC collection
        model: null // the search bar
    },

    initialize: function (models, options) {
        this.collection.on('reset', this.render, this);

        // store any passed-in options
        this.options = options || {};

        // set default options
        if (typeof this.options.maxSuggestionsRendered === 'undefined') {
            this.options.maxSuggestionsRendered = 10;
        }
    },

    render: function () {
        // add all the new suggestions
        var brandSuggestions = {};
        _.each(this.collection.toJSON(), function (suggestion) {
            if (!brandSuggestions[suggestion.provider]) {
                brandSuggestions[suggestion.provider] = [];
            }

            brandSuggestions[suggestion.provider].push(suggestion);
        }, this);

        // remove suggestions until we have the correct number
        while (_.flatten(brandSuggestions).length >
                this.options.maxSuggestionsRendered) {
            // remove the last suggestion of the brand with the most suggestions
            _.max(brandSuggestions, function (s) { return _.size(s); }).pop();
        }

        // clear out the old suggestions
        this.$el.children().remove();

        // add the new suggestions
        _.each(_.flatten(brandSuggestions), function (suggestion) {
            this.$el.append(this.template(suggestion));
        }, this);

        return this;
    },

    clickSuggestion: function (e) {
        // set the query to the clicked value, then reset the suggestions
        this.model.set({query: $(e.target).text()});
        this.collection.reset();
    }
});

//
// ENTRY POINT
//

$(function () {
    var searchBar = new SearchBar();
    var searchBarView = new SearchBarView({
        model: searchBar
    });

    var acSuggestionList = new AutocompleteSuggestionList();
    var acSuggestionListView = new AutocompleteSuggestionListView({
        collection: acSuggestionList,
        model: searchBar,
        el: $('#search-bar ul')
    }, {maxSuggestionsRendered: 16});

    searchBar.set({acSuggestionList: acSuggestionList});
});

});
