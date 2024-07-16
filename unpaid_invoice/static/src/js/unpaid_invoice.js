odoo.define('export_pdf.print_pdf',function(require){
    "use strict";

var ListController = require('web.ListController');
ListController.include({
   renderButtons: function($node) {
   this._super.apply(this, arguments);
       if (this.$buttons) {
         this.$buttons.find('.o_list_export_pdf') ;
       }
   }, 
   });
});