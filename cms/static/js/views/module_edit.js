(function() {
    'use strict';

    // eslint-disable-next-line no-var
    var __hasProp = {}.hasOwnProperty,
        __extends = function(child, parent) {
            // eslint-disable-next-line no-var
            var key;
            // eslint-disable-next-line no-restricted-syntax
            for (key in parent) {
                if (__hasProp.call(parent, key)) {
                    child[key] = parent[key];
                }
            }
            function Ctor() {
                this.constructor = child;
            }
            Ctor.prototype = parent.prototype;
            child.prototype = new Ctor();
            child.__super__ = parent.prototype;
            return child;
        };

    // eslint-disable-next-line no-undef
    define(['jquery', 'underscore', 'gettext', 'xblock/runtime.v1', 'js/views/xblock', 'js/views/modals/edit_xblock'],
        function($, _, gettext, XBlock, XBlockView, EditXBlockModal) {
            // eslint-disable-next-line no-var
            var ModuleEdit = (function(_super) {
                // eslint-disable-next-line no-use-before-define
                __extends(ModuleEdit, _super);

                // eslint-disable-next-line no-shadow
                function ModuleEdit() {
                    return ModuleEdit.__super__.constructor.apply(this, arguments);
                }

                ModuleEdit.prototype.tagName = 'li';

                ModuleEdit.prototype.className = 'component';

                ModuleEdit.prototype.editorMode = 'editor-mode';

                ModuleEdit.prototype.events = {
                    'click .edit-button': 'clickEditButton',
                    'click .delete-button': 'onDelete'
                };

                ModuleEdit.prototype.initialize = function() {
                    this.onDelete = this.options.onDelete;
                    return this.render();
                };

                // eslint-disable-next-line consistent-return
                ModuleEdit.prototype.loadDisplay = function() {
                    // eslint-disable-next-line no-var
                    var xblockElement;
                    xblockElement = this.$el.find('.xblock-student_view');
                    if (xblockElement.length > 0) {
                        return XBlock.initializeBlock(xblockElement);
                    }
                };

                ModuleEdit.prototype.createItem = function(parent, payload, callback) {
                    // eslint-disable-next-line no-var
                    var _this = this;
                    if (_.isNull(callback)) {
                        callback = function() {};
                    }
                    payload.parent_locator = parent;
                    return $.postJSON(this.model.urlRoot + '/', payload, function(data) {
                        _this.model.set({
                            id: data.locator
                        });
                        _this.$el.data('locator', data.locator);
                        _this.$el.data('courseKey', data.courseKey);
                        return _this.render();
                    }).success(callback);
                };

                // eslint-disable-next-line consistent-return
                ModuleEdit.prototype.loadView = function(viewName, target, callback) {
                    // eslint-disable-next-line no-var
                    var _this = this;
                    if (this.model.id) {
                        return $.ajax({
                            url: '' + (decodeURIComponent(this.model.url())) + '/' + viewName,
                            type: 'GET',
                            cache: false,
                            headers: {
                                Accept: 'application/json'
                            },
                            success: function(fragment) {
                                return _this.renderXBlockFragment(fragment, target).done(callback);
                            }
                        });
                    }
                };

                ModuleEdit.prototype.render = function() {
                    // eslint-disable-next-line no-var
                    var _this = this;
                    return this.loadView('student_view', this.$el, function() {
                        _this.loadDisplay();
                        return _this.delegateEvents();
                    });
                };

                ModuleEdit.prototype.clickEditButton = function(event) {
                    // eslint-disable-next-line no-var
                    var modal;
                    event.preventDefault();
                    modal = new EditXBlockModal();
                    return modal.edit(this.$el, this.model, {
                        refresh: _.bind(this.render, this)
                    });
                };

                return ModuleEdit;
            }(XBlockView));
            return ModuleEdit;
        });
}).call(this);
