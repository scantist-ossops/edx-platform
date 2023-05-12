// eslint-disable-next-line no-unused-vars
/* globals DiscussionUtil, MathJax */
(function() {
    'use strict';

    // eslint-disable-next-line no-var
    var __hasProp = {}.hasOwnProperty,
        __extends = function(child, parent) {
            /* eslint-disable-next-line no-var, no-restricted-syntax */
            for (var key in parent) {
                if (__hasProp.call(parent, key)) {
                    child[key] = parent[key];
                }
            }
            function ctor() {
                this.constructor = child;
            }

            ctor.prototype = parent.prototype;
            child.prototype = new ctor();
            child.__super__ = parent.prototype;
            return child;
        };

    // eslint-disable-next-line no-undef
    if (typeof Backbone !== 'undefined' && Backbone !== null) {
        this.DiscussionThreadProfileView = (function(_super) {
            // eslint-disable-next-line no-use-before-define
            __extends(DiscussionThreadProfileView, _super);

            function DiscussionThreadProfileView() {
                return DiscussionThreadProfileView.__super__.constructor.apply(this, arguments);
            }

            DiscussionThreadProfileView.prototype.render = function() {
                // eslint-disable-next-line no-var
                var params;
                this.convertMath();
                this.abbreviateBody();
                params = $.extend(this.model.toJSON(), {
                    permalink: this.model.urlFor('retrieve')
                });
                if (!this.model.get('anonymous')) {
                    params = $.extend(params, {
                        user: {
                            username: this.model.username,
                            user_url: this.model.user_url
                        }
                    });
                }
                edx.HtmlUtils.setHtml(
                    this.$el,
                    edx.HtmlUtils.template($('#profile-thread-template').html())(params)
                );
                this.$('span.timeago').timeago();
                DiscussionUtil.typesetMathJax(this.$('.post-body'));
                return this;
            };

            DiscussionThreadProfileView.prototype.convertMath = function() {
                // eslint-disable-next-line no-var
                var htmlSnippet = DiscussionUtil.markdownWithHighlight(this.model.get('body'));
                this.model.set('markdownBody', htmlSnippet);
            };

            DiscussionThreadProfileView.prototype.abbreviateBody = function() {
                // eslint-disable-next-line no-var
                var abbreviated;
                abbreviated = DiscussionUtil.abbreviateHTML(this.model.get('markdownBody'), 140);
                this.model.set('abbreviatedBody', abbreviated);
            };

            return DiscussionThreadProfileView;
        // eslint-disable-next-line no-undef
        }(Backbone.View));
    }
}).call(window);
