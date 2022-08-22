odoo.define('memo.hide_edit_buttons', function (require) {
    "use strict";
    let FormView = require('web.FormView');
    var session = require('web.session');
    var Model = require('web.Model');
    var mymodel = new Model('memo.model');
    FormView.include({
        load_record: function (record) {
            if (record && this.$buttons) { 
                if ((this.model === "memo.model") && (record.state != "submit")){
                    if (session.uid !== record.demo_staff){
                        console.log('User '+String(record.demo_staff)+'UID '+session.uid)
                        this.$buttons.find('.o_form_buttons_view').hide();
                            console.log('Hidden at user memo')
                    }
                    else {
                                this.$buttons.find('.o_form_buttons_view').show();
                                console.log('Shown for company memo')
                    } 
                } 
            }
            return this._super(record);
        }
    });
});
// if (record.users_followers){
                        //     if (record.res_users[0] === session.uid) {
                        //         this.$buttons.find('.oe_highlight').hide();
                                //$('#forward_memo').hide();
                                // console.log(record.users_followers[0]).btn btn-sm oe_highlight fvm
                            //     console.log('nnnn')

                            // } 
                            // else {
                            //     this.$buttons.find('.btn btn-sm oe_highlight fvm').hide();
                            //     console.log('Nonexx')

                            // }
// var Users = new openerp.Model('res.users');
// Users.query(['name', 'login', 'user_email', 'signature'])
//      .filter([['active', '=', true], ['company_id', '=', main_company]])
//      .limit(15)
//      .all().then(function (users) {
//     // do work with users records, you can access only fields said in query
//      for(i in users){
//          console.log(i.name)
//      }
//  });
// function Hider(){
//     mymodel.query(['user_id']).filter([['state', '!=', 'submit']]).all().then(function(user) {
//         for(i in user){
//             // do something
//             if session.uid === record
//         }
//     })

// }

// var Model = require('web.Model');
// var ResCompany = new Model('res.company');
// ResCompany.query(['name'])
//    .filter([['id', '=', 1]])
//    .first()
//    .then(function (company){
//         CompanyName = company.name;
//     });
