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
    'text!/static/templates/results.html.mustache',
    'text!/static/templates/result.html.mustache'
],
function ($, _, Backbone, Mustache, tmplSearchBar, tmplResults, tmplResult) {

// the search bar
var SearchBar = Backbone.Model.extend({
    defaults: {
        query: '',
        resultsList: null
    },

    updateResults: _.debounce(function () {
        // update search results
        this.get('resultsList').updateResults(this.get('query'));
    }, 200)
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
        this.model.updateResults();
    },

    mirrorQuery: function () {
        // copy the model's query option into the input if not focused
        if (!this.$input.is(':focus')) {
            this.$input.val(this.model.get('query'));
        }
        this.$input.focus();
    }
});

// a generic search result that encompasses all types
var Result = Backbone.Model.extend({
    defaults: {
        type: null,
        provider: null,

        title: '',
        series_title: '',
        description: '',

        season_number: null,
        episode_number: null,
        season_count: null,
        episode_count: null,

        duration_seconds: 0,
        rating_fraction: 0,

        url: null,
        image_url: null
    }
});

var ResultList = Backbone.Collection.extend({
    model: Result,
    url: '/search/find',

    updateResults: function (query) {
        var xhr = $.getJSON(this.url, {'query': query});

        // update the collection on reset
        xhr.success(_.bind(function (data) {
            this.reset(data.results);
        }, this));
    }
});

var ResultListView = Backbone.View.extend({
    template: Mustache.compile(tmplResults),
    itemTemplate: Mustache.compile(tmplResult),

    defaults: {
        collection: null, // the result collection
        model: null // the search bar
    },

    initialize: function (models, options) {
        this.collection.on('reset', this.render, this);

        // build the container and add it to the body
        this.setElement($(this.template()));
        this.$el.appendTo($('body'));

        // store any passed-in options
        this.options = options || {};

        // set default options
        if (typeof this.options.maxResultsRendered === 'undefined') {
            this.options.maxResultsRendered = 15;
        }
    },

    render: function () {
        // NOTE: functions identically to the render in the AC suggestions

        var brandResults = {};
        _.each(this.collection.toJSON(), function (result) {
            if (!brandResults[result.provider]) {
                brandResults[result.provider] = [];
            }

            brandResults[result.provider].push(result);
        }, this);

        while (_.flatten(brandResults).length >
                this.options.maxResultsRendered) {
            _.max(brandResults, function (s) { return _.size(s); }).pop();
        }

        this.$el.children().remove();

        _.each(_.flatten(brandResults), function (result) {
            this.$el.append(this.itemTemplate(result));
        }, this);

        return this;
    }
});

//
// ENTRY POINT
//

$(function () {
    // where searching takes place
    var searchBar = new SearchBar();
    var searchBarView = new SearchBarView({
        model: searchBar
    });

    // search results
    var resultsList = new ResultList();
    var resultsListView = new ResultListView({
        model: searchBar,
        collection: resultsList
    }, {maxResultsRendered: 15});

    // add the results collection to the search bar
    searchBar.set({resultsList: resultsList});
});

});
