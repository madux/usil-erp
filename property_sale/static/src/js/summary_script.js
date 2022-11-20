odoo.define('property_sale.dashboard_summary_view', function (require) {
    'use strict';
  
    // var session = require('web.session');
    var core = require('web.core');
    var Model = require('web.Model');
    var Widget = require('web.Widget');
    var session = require('web.session');
    // var rpc = require('web.rpc');
  
    var session = require('web.session');
    var core = require('web.core');
    var utils = require('web.utils');
  
    var ajax = require('web.ajax');
  
    var _t = core._t;
    var _lt = core._lt;
    var QWeb = core.qweb;
  
    jQuery(document).ready(function(){
      var Init = function(){ 
      var BuildingModel = new Model('project.configs');
      let mainx_axis = null;
      let mainy_axis = null; 
        RenderProjects()
        jQuery('.bar_graph').show(); 
        jQuery('#datepicker1summ').hide(); 
        jQuery('#datepicker2summ').hide();
        jQuery('.limit-div').hide();

        jQuery('#sales_by_project_select_summ').hide(); 
        
        $('#filter_based_on_general').change(function(){
          if($(this).val() == "Filter By Date/ Project"){
              $('#datepicker1summ').show();
              $('#datepicker2summ').show();
              jQuery('#sales_by_project_select_summ').show(); 
  
              $('#datepicker1summ').prop('required', true);
            $('#datepicker2summ').prop('required', true);
            jQuery('#sales_by_project_select_summ').prop('required', true);
  
          }else{
            $('#datepicker1summ').hide();
            $('#datepicker2summ').hide();
            jQuery('#sales_by_project_select_summ').hide(); 
            $('#datepicker1summ').prop('required', false);
            $('#datepicker2summ').prop('required', false);
            jQuery('#sales_by_project_select_summ').prop('required', false);
            jQuery('#sales_by_project_select_summ').val("");
            jQuery('#datepicker1summ').val("");
            jQuery('#datepicker2summ').val("");
            console.log('Datepicker==>', jQuery('#datepicker2summ').val())
  
          }
        });
  
        function RemoveOptions(){
          $('#is_option_all_sum').prop('checked', false);
          $('#is_sold_filter_summ').prop('checked', false);
          $('#is_unsold_filter_summ').prop('checked', false);
          $('#is_reserved_filter_summ').prop('checked', false);
        }
        function RenderProjects(){
          BuildingModel.call('get_lists_of_projects', [null],
            {context: ''}).then(function (data) {
                _.each(data, function(result){
                var projectsIDS = [];
                projectsIDS.push(result);
                console.log('Projects Found', projectsIDS)
                jQuery('#sales_by_project_select_summ').append(
                    jQuery('<option value="' + result + '">' + result + '</option>')
                  );
              });
          });
        }

        $('#sales_by_project_select_summ').change(function(){
          if ($(this).val()){
            BackendDataCall();
          }
        })

        $('#datepicker1summ').change(function(){
          if ($(this).val()){
            BackendDataCall();
          }
        })

        $('#datepicker2summ').change(function(){
          if (!$('#datepicker1summ').val())
            {
              alert("Please Enter Start Date!!!")
            }else {
              BackendDataCall();
            }
        })
  
        $('#sales_by_analysis_select').change(function(){
          RemoveOptions()
          if($(this).val() == "Projects"){
                var xproject = $('#sales_by_project_select_summ').val() ? $('#sales_by_project_select_summ').val() : null;
                var xdatefrom = $('#datepicker1summ').val() ? $('#datepicker1summ').val() : null;
                var xdateto = $('#datepicker2summ').val() ? $('#datepicker2summ').val() : null;
                var sales = $('#datepicker2summ').val() ? "All" : "NoDatefilter";

                console.log('IIIIIIIIIIIIIIIIIIIIIIII ==> '+sales+' Date set for select project '+ xdatefrom+' and '+ xdateto+' For project: '+xproject);
    
                BuildingModel.call('summary_project_report', [[0],xproject,xdatefrom,xdateto,"All", "True"],
                {context: ''}).then(function (data) {
                    var Buildings = [];
                    var Building_Counter = 1;
                    var x_axis = [];
                    var y_axis = [];
                    x_axis = data['plot_category']
                    y_axis = data['plot_category_values']
                    mainx_axis = x_axis;
                    mainy_axis = y_axis;

                    $('#tot_sold').text(numberWithCommas(data['sold_units']))
                    $('#tot_sellable').text('N ' + numberWithCommas(data['total_sellable']))
                    // $('#tot_reserved').text('N' + data['total_amount_reserved'])

                    $('#tot_units').text(numberWithCommas(data['total_units']))
                    $('#tot_unsold').text(numberWithCommas(data['unsold_units']))
                    $('#tot_reserved').text(numberWithCommas(data['reserved_units']))
                    console.log('RESERVED UNITS IS '+ data['reserved_units'])
                    
                    $('#actual_sales_id').text('N ' + numberWithCommas(data['total_amount_sold']))
                    $('#percent_balance_collected').text('% ' +data['outstanding_amount'])
                    $('#percent_recieved').text('N ' + numberWithCommas(data['received_percentage']))
                    $('#balance_collectible').text('N ' + numberWithCommas(data['outstanding_amount']))
                    $('#deposit_received').text('N ' + numberWithCommas(data['received_paid']))
                    $('#total_discount').text('N ' + numberWithCommas(data['total_percentage_discount']))
                    $('#actual_sale_diff').text('N ' + numberWithCommas(data['total_actual_sale_diff']))
                    

                    console.log('Total amount ==> '+data['total_amount_sold']+ 'Balance==> '+data['outstanding_amount']);
                    
                    jQuery('.grider').empty();
                    jQuery('.grider').append(jQuery('<div name="bar_graph_summ" id="bar-div-summ" class="bar_graph"> \
                    <a class="button-summary buttonradius block mt-2 text-center" href="#feedback">Bar Graph</a>\
                    <canvas id="bar-chart2-summ" width="200" height="80"/><p/>\
                    </div><p/>'))
                    
                    jQuery('.grider').append(jQuery('<div name="donut_graph_summ" id="donut-div-summ" class="donut_graph mb-3"> \
                    <a class="button-summary buttonradius block mt-2 text-center" href="#feedback">Donut Graph</a>\
                    <canvas id="donut-chart-summ" width="200" height="100"/><p/>\
                    </div><p/>'))

                    jQuery('.grider').append(jQuery('<div name="horizontal_bar_summ" id="horizontal-div-summ" class="pie_graph"> \
                    <a class="button-summary buttonradius block mt-2 text-center" href="#feedback">Horizontal Chart</a>\
                    <canvas id="horizonbar-chart-summ" width="200" height="100"/><p/>\
                    </div><p/>'))

                    GraphDynamicDisplay(x_axis, y_axis, "bar-chart2-summ", "bar");
                    GraphDynamicDisplay(x_axis, y_axis, "donut-chart-summ", "doughnut");
                    GraphDynamicDisplay(x_axis, y_axis, "horizonbar-chart-summ", "horizontalBar");
                    
                }); 
            }else{console.log('not selected')}
        })

        // Function to call Database values
        function BackendDataCall(){
            var xproject = $('#sales_by_project_select_summ').val() ? $('#sales_by_project_select_summ').val() : null;
              var xdatefrom = $('#datepicker1summ').val() ? $('#datepicker1summ').val() : null;
              var xdateto = $('#datepicker2summ').val() ? $('#datepicker2summ').val() : null;
              var sales = $('#datepicker2summ').val() ? "All" : "NoDatefilter";
              console.log('Rendered Charts For ==> '+sales+' Date set for selected project'+ xdatefrom+' and '+ xdateto+' For project: '+xproject);
              BuildingModel.call('summary_project_report', [[0],xproject,xdatefrom,xdateto,"All", "True"],
              {context: ''}).then(function (data) {
                  var x_axis = [];
                  var y_axis = [];
                  x_axis = data['plot_category']
                  y_axis = data['plot_category_values']
                  mainx_axis = x_axis;
                  mainy_axis = y_axis;

                  $('#tot_sold').text(numberWithCommas(data['sold_units']))
                  $('#tot_sellable').text('N ' + numberWithCommas(data['total_sellable']))
                  $('#tot_units').text(numberWithCommas(data['total_units']))
                  $('#tot_unsold').text(numberWithCommas(data['unsold_units']))
                  $('#tot_reserved').text(numberWithCommas(data['reserved_units']))
                  console.log('RESERVED UNITS IS '+ data['reserved_units'])
                  
                  $('#actual_sales_id').text('N ' + numberWithCommas(data['total_amount_sold']))
                  $('#percent_balance_collected').text('% ' +data['outstanding_amount'])
                  $('#percent_recieved').text('N ' + numberWithCommas(data['received_percentage']))
                  $('#balance_collectible').text('N ' + numberWithCommas(data['outstanding_amount']))
                  $('#deposit_received').text('N ' + numberWithCommas(data['received_paid']))
                  $('#total_discount').text('N ' + numberWithCommas(data['total_percentage_discount']))
                  $('#actual_sale_diff').text('N ' + numberWithCommas(data['total_actual_sale_diff']))
                  console.log('Total amount ==> '+data['total_amount_sold']+ 'Balance==> '+data['outstanding_amount']);
                  
                  jQuery('.grider').empty();
                  jQuery('.grider').append(jQuery('<div name="bar_graph_summ" id="bar-div-summ" class="bar_graph" style="margin-right: 6px;"> \
                  <a class="button-summary buttonradius block mt-2 text-center" href="#feedback">Bar Graph</a>\
                  <canvas id="bar-chart2-summ" width="200" height="80"/><p/>\
                  </div><p/>'))
                  
                  jQuery('.grider').append(jQuery('<div name="donut_graph_summ" id="donut-div-summ" class="donut_graph mb-3" style="margin-right: 6px;"> \
                  <a class="button-summary buttonradius block mt-2 text-center" href="#feedback">Donut Graph</a>\
                  <canvas id="donut-chart-summ" width="200" height="100"/><p/>\
                  </div><p/>'))

                  jQuery('.grider').append(jQuery('<div name="horizontal_bar_summ" id="horizontal-div-summ" class="pie_graph" style="margin-right: 6px;"> \
                  <a class="button-summary buttonradius block mt-2 text-center" href="#feedback">Horizontal Chart</a>\
                  <canvas id="horizonbar-chart-summ" width="200" height="100"/><p/>\
                  </div><p/>'))

                  GraphDynamicDisplay(x_axis, y_axis, "bar-chart2-summ", "bar");
                  GraphDynamicDisplay(x_axis, y_axis, "donut-chart-summ", "doughnut");
                  GraphDynamicDisplay(x_axis, y_axis, "horizonbar-chart-summ", "horizontalBar");
                  
              });
        }
        
        // Function to format number as Commas
        function numberWithCommas(x) {
            return x.toString().replace(/\B(?<!\.\d*)(?=(\d{3})+(?!\d))/g, ",");
        }

        // Function to render Charts
        function GraphDynamicDisplay(mainx_axis, mainy_axis, canvasid, viewid){
          new Chart(document.getElementById(canvasid), {
            type: viewid,
            data: {
                labels: mainx_axis,
                datasets: [{ 
                    data: mainy_axis,
                    label: "Summary Report",
                    borderColor: "#000000",
                    backgroundColor: ['rgba(255, 99, 132, 0.2)',
                                    'rgba(54, 162, 235, 0.2)',
                                    'rgba(255, 206, 86, 0.2)',
                                    'rgba(75, 192, 192, 0.2)',
                                    'rgba(153, 102, 255, 0.2)',
                                    'rgba(255, 159, 64, 0.2)'
                                    ],
                    borderColor: [
                        'rgba(255, 99, 132, 1)',
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 206, 86, 1)',
                        'rgba(75, 192, 192, 1)',
                        'rgba(153, 102, 255, 1)',
                        'rgba(255, 159, 64, 1)'
                    ],
                    borderWidth: 1,
                    fill: true,
                }                      
                ]
            },
  
            options: {
                title: {
                display: true,
                text: 'Sales Made by Project'
                }
            }
            }); 
  
        }
           
        $('#is_option_all_sum').change(function(){
          if ($(this).prop('checked')) {
              // DynamicMethod(null,null,null,null,null)
              $('#is_sold_filter_summ').prop('checked', false);
              $('#is_unsold_filter_summ').prop('checked', false);
              $('#is_reserved_filter_summ').prop('checked', false);
  
              var xproject = $('#sales_by_project_select_summ').val() ? $('#sales_by_project_select_summ').val() : null;
              var xdatefrom = $('#datepicker1summ').val() ? $('#datepicker1summ').val() : null;
              var xdateto = $('#datepicker2summ').val() ? $('#datepicker2summ').val() : null;
              // var sales = $('#datepicker2summ').val() ? "NoDatefilter" : "All";
            console.log('HereX ==>  Date set for select project ' +xdatefrom+' and '+ xdateto+' For project: '+xproject);
  
            BuildingModel.call('summary_project_report', [[0],xproject,xdatefrom,xdateto,"NoDatefilter", "True"],
            {context: ''}).then(function (data) {
              var Buildings = [];
              var Building_Counter = 1;
              var x_axis = [];
              var y_axis = [];
              x_axis = data['plot_category']
              y_axis = data['plot_category_values']
              mainx_axis = x_axis;
              mainy_axis = y_axis;
              console.log('x axis and mainx '+x_axis+' - '+mainx_axis);
              console.log('y axis',y_axis)
              
              jQuery('.grider_summ').empty();
              jQuery('.grider_summ').append(jQuery('<div name="bar_graph_summ" id="bar-div-summ" class="bar_graph"> \
              <a class="btn-primary block mt-2 text-center" href="#feedback">Bar Graph</a>\
              <canvas id="bar-chart2-summ" width="200" height="80"/><p/>\
              </div><p/>'))
              
              jQuery('.grider_summ').append(jQuery('<div name="donut_graph_summ" id="donut-div-summ" class="donut_graph mb-3"> \
              <a class="btn-primary block mt-2 text-center" href="#feedback">Donut Graph</a>\
              <canvas id="donut-chart-summ" width="200" height="100"/><p/>\
              </div><p/>'))

              jQuery('.grider_summ').append(jQuery('<div name="horizontal_bar_summ" id="horizontal-div-summ" class="donut_graph"> \
              <a class="btn-primary block mt-2 text-center" href="#feedback">Horizontal Chart</a>\
              <canvas id="horizonbar-chart-summ" width="200" height="100"/><p/>\
              </div><p/>'))

              GraphDynamicDisplay(x_axis, y_axis, "bar-chart2-summ", "bar");
              GraphDynamicDisplay(x_axis, y_axis, "donut-chart-summ", "doughnut");
              GraphDynamicDisplay(x_axis, y_axis, "horizonbar-chart-summ", "horizontalBar");
              
            }); 
            console.log('All fired!!!')
               
          } 
  
        })
  
        $('#is_sold_filter_summ').change(function(){
          if ($(this).prop('checked')) {
   
              $('#is_unsold_filter_summ').prop('checked', false);
              $('#is_reserved_filter_summ').prop('checked', false);
              $('#is_option_all_sum').prop('checked', false);
  
              var xproject = $('#sales_by_project_select_summ').val() ? $('#sales_by_project_select_summ').val() : null;
              var xdatefrom = $('#datepicker1summ').val() ? $('#datepicker1summ').val() : null;
              var xdateto = $('#datepicker2summ').val() ? $('#datepicker2summ').val() : null;
  
              BuildingModel.call('summary_project_report', [[0],xproject,xdatefrom,xdateto,"Sold", "True"],
                {context: ''}).then(function (data) {
                var Buildings = [];
                var Building_Counter = 1;
                var x_axis = [];
                var y_axis = [];
                x_axis = data['plot_category']
                y_axis = data['plot_category_values']
                mainx_axis = x_axis;
                mainy_axis = y_axis;
                console.log('x axis and mainx '+x_axis+' - '+mainx_axis);
                console.log('y axis',y_axis)
                
                jQuery('.grider_summ').empty();
                jQuery('.grider_summ').append(jQuery('<div name="bar_graph_summ" id="bar-div-summ" class="bar_graph"> \
                <a class="btn-primary block mt-2 text-center" href="#feedback">Bar Graph</a>\
                <canvas id="bar-chart2-summ" width="200" height="80"/><p/>\
                </div><p/>'))
                
                jQuery('.grider_summ').append(jQuery('<div name="donut_graph_summ" id="donut-div-summ" class="donut_graph mb-3"> \
                <a class="btn-primary block mt-2 text-center" href="#feedback">Donut Graph</a>\
                <canvas id="donut-chart-summ" width="200" height="100"/><p/>\
                </div><p/>'))

                jQuery('.grider_summ').append(jQuery('<div name="horizontal_bar_summ" id="horizontal-div-summ" class="donut_graph"> \
                <a class="btn-primary block mt-2 text-center" href="#feedback">Horizontal Chart</a>\
                <canvas id="horizonbar-chart-summ" width="200" height="100"/><p/>\
                </div><p/>'))

                GraphDynamicDisplay(x_axis, y_axis, "bar-chart2-summ", "bar");
                GraphDynamicDisplay(x_axis, y_axis, "donut-chart-summ", "doughnut");
                GraphDynamicDisplay(x_axis, y_axis, "horizonbar-chart-summ", "horizontalBar");
                
                });
              console.log('Sold')
               
          } 
  
        })
  
        $('#is_unsold_filter_summ').change(function(){
          if ($(this).prop('checked')) {
              // DynamicMethod(null,null,null, "UnSold")
              $('#is_sold_filter_summ').prop('checked', false);
              $('#is_reserved_filter_summ').prop('checked', false);
              $('#is_option_all_sum').prop('checked', false);
              var xproject = $('#sales_by_project_select_summ').val() ? $('#sales_by_project_select_summ').val() : null;
              var xdatefrom = $('#datepicker1summ').val() ? $('#datepicker1summ').val() : null;
              var xdateto = $('#datepicker2summ').val() ? $('#datepicker2summ').val() : null;
              console.log('Reserved ==>  Date set for select project ' +xdatefrom+' and '+ xdateto+' For project: '+xproject);
  
              BuildingModel.call('summary_project_report', [[0],xproject,xdatefrom,xdateto,"UnSold", "True"],
                {context: ''}).then(function (data) {
                var x_axis = [];
                var y_axis = [];
                x_axis = data['plot_category']
                y_axis = data['plot_category_values']
                mainx_axis = x_axis;
                mainy_axis = y_axis;
                console.log('x axis and mainx '+x_axis+' - '+mainx_axis);
                console.log('y axis',y_axis)
                
                jQuery('.grider_summ').empty();
                jQuery('.grider_summ').append(jQuery('<div name="bar_graph_summ" id="bar-div-summ" class="bar_graph"> \
                <a class="btn-primary block mt-2 text-center" href="#feedback">Bar Graph</a>\
                <canvas id="bar-chart2-summ" width="200" height="80"/><p/>\
                </div><p/>'))
                
                jQuery('.grider_summ').append(jQuery('<div name="donut_graph_summ" id="donut-div-summ" class="donut_graph mb-3"> \
                <a class="btn-primary block mt-2 text-center" href="#feedback">Donut Graph</a>\
                <canvas id="donut-chart-summ" width="200" height="100"/><p/>\
                </div><p/>'))

                jQuery('.grider_summ').append(jQuery('<div name="horizontal_bar_summ" id="horizontal-div-summ" class="donut_graph"> \
                <a class="btn-primary block mt-2 text-center" href="#feedback">Horizontal Chart</a>\
                <canvas id="horizonbar-chart-summ" width="200" height="100"/><p/>\
                </div><p/>'))

                GraphDynamicDisplay(x_axis, y_axis, "bar-chart2-summ", "bar");
                GraphDynamicDisplay(x_axis, y_axis, "donut-chart-summ", "doughnut");
                GraphDynamicDisplay(x_axis, y_axis, "horizonbar-chart-summ", "horizontalBar");
                
                });
                //
              console.log('UnSold')
               
          } 
  
        })
  
        $('#is_reserved_filter_summ').change(function(){
          if ($(this).prop('checked')) {
              console.log('Yes Clicked')
              $('#is_sold_filter_summ').prop('checked', false);
              $('#is_unsold_filter_summ').prop('checked', false);
              $('#is_option_all_sum').prop('checked', false);
  
              var xproject = $('#sales_by_project_select_summ').val() ? $('#sales_by_project_select_summ').val() : null;
              var xdatefrom = $('#datepicker1summ').val() ? $('#datepicker1summ').val() : null;
              var xdateto = $('#datepicker2summ').val() ? $('#datepicker2summ').val() : null;
              console.log('Reserved ==>  Date set for select project ' +xdatefrom+' and '+ xdateto+' For project: '+xproject);
  
  
              BuildingModel.call('summary_project_report', [[0],xproject,xdatefrom,xdateto,"Reserved", "True"],
                {context: ''}).then(function (data) {
                var x_axis = [];
                var y_axis = [];
                x_axis = data['plot_category']
                y_axis = data['plot_category_values']
                mainx_axis = x_axis;
                mainy_axis = y_axis;
                console.log('x axis and mainx '+x_axis+' - '+mainx_axis);
                console.log('y axis',y_axis)
                
                jQuery('.grider_summ').empty();
                jQuery('.grider_summ').append(jQuery('<div name="bar_graph_summ" id="bar-div-summ" class="bar_graph"> \
                <a class="btn-primary block mt-2 text-center" href="#feedback">Bar Graph</a>\
                <canvas id="bar-chart2-summ" width="200" height="80"/><p/>\
                </div><p/>'))
                
                jQuery('.grider_summ').append(jQuery('<div name="donut_graph_summ" id="donut-div-summ" class="donut_graph mb-3"> \
                <a class="btn-primary block mt-2 text-center" href="#feedback">Donut Graph</a>\
                <canvas id="donut-chart-summ" width="200" height="100"/><p/>\
                </div><p/>'))

                jQuery('.grider_summ').append(jQuery('<div name="horizontal_bar_summ" id="horizontal-div-summ" class="donut_graph"> \
                <a class="btn-primary block mt-2 text-center" href="#feedback">Horizontal Chart</a>\
                <canvas id="horizonbar-chart-summ" width="200" height="100"/><p/>\
                </div><p/>'))

                GraphDynamicDisplay(x_axis, y_axis, "bar-chart2-summ", "bar");
                GraphDynamicDisplay(x_axis, y_axis, "donut-chart-summ", "doughnut");
                GraphDynamicDisplay(x_axis, y_axis, "horizonbar-chart-summ", "horizontalBar");
                
                });
                //
              console.log('Reserved')
               
          } 
  
        })
  
      }
      
      var init = Init();
    });
  
  });
  
   