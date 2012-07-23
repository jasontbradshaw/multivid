require.config({
    paths: {
        jquery: "/static/js/libs/jquery-min",
        underscore: "/static/js/libs/underscore-min",
        backbone: "/static/js/libs/backbone-min",
        mustache: "/static/js/libs/mustache",
    },
    shim: {
        jquery: {
            exports: "$"
        },
        underscore: {
            exports: "_"
        },
        backbone: {
            deps: ["underscore", "jquery"],
            exports: "Backbone"
        }
    }
});

require(["jquery", "underscore","backbone", "mustache"],
function ($, _, Backbone, Mustache) {
$(function () {

// the search bar
var SearchBar = Backbone.Model.extend({
    initialize: function () {
        this.bind("change:position", function () {
            // TODO: change CSS class
            console.log("position changed!");
        });
    },
    defaults: {
        position: "center" // the current location of the search bar/box
    }
});

var SearchBarView = Backbone.View.extend({
    id: "search-bar",
    className: "search-bar-position-center"
});

// a suggestion below the search bar
var AutocompleteSuggestion = Backbone.Model.extend({
    defaults: {
        originator: null,
        text: ""
    }
});

var AutocompleteSuggestionCollection = Backbone.Collection.extend({
    model: AutocompleteSuggestion
});

// ** END **
});
});
