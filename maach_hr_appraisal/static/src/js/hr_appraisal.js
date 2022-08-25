odoo.define('maach_hr_appraisal.hide_edit_button_option', function (require) {
    "use strict";
    let FormView = require('web.FormView');
    var session = require('web.session');
    var Model = require('web.Model');
    FormView.include({
        load_record: function (record) {
            if (record && this.$buttons) {
                if ((this.model === "usl.employee.appraisal") && (record.state != "Draft")){
                    if (session.uid !== 1){
                        if (record.directed_user_id){
                            if (record.directed_user_id.includes(session.uid)){
                                this.$buttons.find('.o_form_buttons_view').show();
                                console.log('show edit button')
                            }
                        else {
                                this.$buttons.find('.o_form_buttons_view').hide();
                                console.log('hide edit button')
                            }
                        } 
                    }
	             } 
                 
            } 
            return this._super(record);
        }
    });
});
