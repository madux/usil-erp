odoo.define('memo.crashManager', function (require) {
        "use strict";
        var ajax = require('web.ajax');
        var core = require('web.core');
        var CrashManager = require('web.CrashManager');
        var Dialog = require('web.Dialog');
        
        var _t = core._t;
        var QWeb = core.qweb; 

        Dialog.include({
            /**
            * @override
                 * This function is invoked after user performs an action after session expiry
            */
            title: _t('Invalid'), subtitle: '',
        })

        
            
        CrashManager.include({
             
    
            /**
             * @override
             * This function is invoked after user performs an action after session expiry
             */
            show_warning: function(error) {
                if (!this.active) {
                    return;
                }
                return new Dialog(this, {
                    size: 'medium',
                    title: _t("Validation Message"),
                    subtitle: _t("***"), //error.data.title,
                    $content: $(QWeb.render('CrashManager.warning', {error: error}))
                }).open();
            },

            show_error: function(error) {
                if (!this.active) {
                    return;
                    }
                    var dialog = new Dialog(this, {
                        title: _t("Warning! Invalid Input"), 
                    });

                },

        });
    
    });

    function DialogAlert(message){
        return alert('Error in Validation')
    }


    
    