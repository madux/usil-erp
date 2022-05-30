odoo.define('property_sale.dashboard_xxxxview', function (require) {
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
    var Users = new Model('project.configs');
    var BuildingModel = new Model('project.configs');
    let mainx_axis = null;
    let mainy_axis = null;
     
    Users.call('get_lists_of_projects', [null],
                {context: ''}).then(function (data) {
                    _.each(data, function(result){
                    var projectsIDS = [];

                    projectsIDS.push(result);
                    console.log('DATA==>', projectsIDS)
                    jQuery('#sales_by_project_select').append(
                        jQuery('<option value="' + result + '">' + result + '</option>')
                      );
                  });
              });

      jQuery('.bar_graph').show(); 
      jQuery('#datepicker1').hide(); 
      jQuery('#datepicker2').hide();
      jQuery('#sales_by_project_select').hide(); 
      
      jQuery('#view_by_analysis_select').change(function(){
        if (jQuery(this).val() == 'doughnut'){
          
          jQuery('.grider').empty();
          jQuery('.grider').append(jQuery('<div name="donut_graph" id="donut-div" class="bar_graph"> \
              <a class="btn-primary block mt-2 text-center" href="#feedback">Donut Graph</a>\
                 <canvas id="donut-chart" width="200" height="100"/>\
             </div>')) 
          GraphDynamicDisplay(mainx_axis, mainy_axis, "donut-chart", "doughnut");
          console.log('X AXIS FOUND', mainx_axis)
          console.log("Selected ==>", jQuery('#view_by_analysis_select').val())
    
        } else if (jQuery(this).val() == 'line'){

          jQuery('.grider').empty();
          jQuery('.grider').append(jQuery('<div name="line_graph" id="line-div" class="bar_graph">\
          <a class="btn-primary block mt-2 text-center" href="#feedback">Line Graph</a>\
          <canvas id="line-chart" width="200" height="50"/><p/>\
          </div><p/>'))
          GraphDynamicDisplay(mainx_axis, mainy_axis, "line-chart", "line");
          console.log('X AXIS FOUND', mainx_axis)
          console.log("Selected ==>", jQuery('#view_by_analysis_select').val())
        }

        else if (jQuery(this).val() =='pie'){

          jQuery('.grider').empty();
          jQuery('.grider').append(jQuery('<div name="pie_graph" id="pie-div" class="bar_graph">\
          <a class="btn-primary block mt-2 text-center" href="#feedback">Pie Graph</a>\
          <canvas id="pie-chart" width="200" height="100"/>\
          </div>'))
          GraphDynamicDisplay(mainx_axis, mainy_axis, "pie-chart", "pie");
          console.log('X AXIS FOUND', mainx_axis)
          console.log("Selected ==>", jQuery('#view_by_analysis_select').val())
        
        }
        else if (jQuery(this).val() =='horizon'){
          jQuery('.grider').empty();
          jQuery('.grider').append(jQuery('<div name="bar_horizon_graph" id="horizon-div" class="bar_graph">\
              <a class="btn-primary block mt-2 text-center" href="#feedback">Horizon Graph</a>\
            <canvas id="hori-chart" width="200" height="50"/>\
          </div>'))
          GraphDynamicDisplay(mainx_axis, mainy_axis, "hori-chart", "horizon");
          console.log('X AXIS FOUND', mainx_axis)
          console.log("Selected ==>", jQuery('#view_by_analysis_select').val())
        
        }


        else if (jQuery(this).val() =='bar'){
          jQuery('.grider').empty();
          jQuery('.grider').append(jQuery('<div name="bar_graph" id="bar-div" class="bar_graph"> \
          <a class="btn-primary block mt-2 text-center" href="#feedback">Bar Graph</a>\
          <canvas id="bar-chart2" width="200" height="80"/><p/>\
          </div><p/>'))
          GraphDynamicDisplay(mainx_axis, mainy_axis, "bar-chart2", "bar");
          console.log('X AXIS FOUND', mainx_axis)
          console.log("Selected ==>", jQuery('#view_by_analysis_select').val())
        
        }

        else if (jQuery(this).val() == 'All'){
          jQuery('#bar-div').show();
          jQuery('#pie-div').show(); 
          jQuery('#horizon-div').show(); 
          jQuery('#donut-div').show(); 
          jQuery('#line-div').show(); 
          jQuery('.grider').empty();
          jQuery('.grider').append(jQuery('<div name="bar_graph" id="bar-div" class="bar_graph">\
              <a class="btn-primary block mt-2 text-center" href="#feedback">Bar Graph</a>\
              <canvas id="bar-chart2" width="200" height="80"/><p/>\
              </div><p/>\
              <div name="line_graph" id="line-div" class="line_graph">\
              <a class="btn-primary block mt-2 text-center" href="#feedback">Line Graph</a>\
                    <canvas id="line-chart" width="200" height="50"/><p/>\
              </div><p/>\
              <div name="pie_graph" id="pie-div" class="pie_graph mb-3">\
              <a class="btn-primary block mt-2 text-center" href="#feedback">Pie Graph</a>\
                  <canvas id="pie-chart" width="200" height="100"/>\
              </div>\
              <div name="donut_graph" id="donut-div" class="donut_graph mb-3">\
                <a class="btn-primary block mt-2 text-center" href="#feedback">Donut Graph</a>\
                  <canvas id="donut-chart" width="200" height="100"/>\
              </div>\
              <div name="bar_horizon_graph" id="horizon-div" class="bar_horizon_graph">\
                  <a class="btn-primary block mt-2 text-center" href="#feedback">Horizon Graph</a>\
                  <canvas id="hori-chart" width="200" height="50"/>\
              </div>'))

              GraphDynamicDisplay(mainx_axis, mainy_axis, "bar-chart2", "bar");
              GraphDynamicDisplay(mainx_axis, mainy_axis, "line-chart", "line");
              GraphDynamicDisplay(mainx_axis, mainy_axis, "pie-chart", "pie");
              GraphDynamicDisplay(mainx_axis, mainy_axis, "donut-chart", "doughnut");
              GraphDynamicDisplay(mainx_axis, mainy_axis, "hori-chart", "horizon");
              console.log('X AXIS FOUND', mainx_axis)
              console.log("Selected ==>", jQuery('#view_by_analysis_select').val())
            }
        })
      
      $('#filter_based_on_general').change(function(){
        if($(this).val() == "Filter By Date/ Project"){
            $('#datepicker1').show();
            $('#datepicker2').show();
            jQuery('#sales_by_project_select').show(); 

            $('#datepicker1').prop('required', true);
          $('#datepicker2').prop('required', true);
          jQuery('#sales_by_project_select').prop('required', true);


        }else{
          $('#datepicker1').hide();
          $('#datepicker2').hide();
          jQuery('#sales_by_project_select').hide(); 
          $('#datepicker1').prop('required', false);
          $('#datepicker2').prop('required', false);
          jQuery('#sales_by_project_select').prop('required', false);
          jQuery('#sales_by_project_select').val("");
          jQuery('#datepicker1').val("");
          jQuery('#datepicker2').val("");
          console.log('Datepicker==>', jQuery('#datepicker2').val())



        }
      });

      function RemoveOptions(){
        $('#is_option_all').prop('checked', false);
        $('#is_sold_filter').prop('checked', false);
        $('#is_unsold_filter').prop('checked', false);
        $('#is_reserved_filter').prop('checked', false);

      }

      $('#sales_by_project_select').change(function(){
        RemoveOptions()
        // RenderGraph("Project");

          var xproject = $('#sales_by_project_select').val() ? $('#sales_by_project_select').val() : null;
          var xdatefrom = $('#datepicker1').val() ? $('#datepicker1').val() : null;
          var xdateto = $('#datepicker2').val() ? $('#datepicker2').val() : null;
          var sales = $('#datepicker2').val() ? "All" : "NoDatefilter";
          console.log('Here ==> '+sales+' Date set for select project'+ xdatefrom+' and '+ xdateto+' For project: '+xproject);

          BuildingModel.call('dynamic_projects_rendering', [[0],xproject,xdatefrom,xdateto,sales],
            {context: ''}).then(function (data) {
              var Buildings = [];
              var Building_Counter = 1;
              var x_axis = [];
              var y_axis = [];
              x_axis = data['list_buildings']
              y_axis = data['list_unsold']
              mainx_axis = x_axis;
              mainy_axis = y_axis;

              console.log('x axis and mainx '+x_axis+' - '+mainx_axis);
              console.log('y axis',y_axis)
              //////
              // GraphDisplay(x_axis, y_axis);
              jQuery('.grider').empty();
              jQuery('.grider').append(jQuery('<div name="bar_graph" id="bar-div" class="bar_graph"> \
              <a class="btn-primary block mt-2 text-center" href="#feedback">Bar Graph</a>\
              <canvas id="bar-chart2" width="200" height="80"/><p/>\
              </div><p/>')) 
              GraphDynamicDisplay(x_axis, y_axis, "bar-chart2", "bar");
              console.log('Graph displayed For projects 2')
                  ///////
            }); 
      })

      function GraphDynamicDisplay(mainx_axis, mainy_axis, canvasid, viewid){
         //////
        new Chart(document.getElementById(canvasid), {
          type: viewid,
          data: {
              labels: mainx_axis,
              datasets: [{ 
                  data: mainy_axis,
                  label: "Property Report",
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

      function GraphDisplay(x_axis, y_axis){
        //////
        new Chart(document.getElementById("bar-chart2"), {
          type: 'bar',
          data: {
              labels: x_axis,
              datasets: [{ 
                  data: y_axis,
                  label: "Property Report",
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


       

      function RenderGraph(x){
        ajax.jsonRpc("/projects/params",
        'call', 
        { 
          'proj': $('#sales_by_project_select').val(), 
          'datefrm': $('#datepicker1').val(), 
          'dateto': $('#datepicker2').val(),
        }).then(function(params){
          var buildname = params['measure_horizontal_building_name'];
          var buildingCount = params['measure_vert_count'];
          var SoldAmount = params['measure_vert_amount'];
          var AmountOwned = params['measure_vert_amount_owned'];
          var AmountPaid = params['measure_vert_amount_paid'];
          console.log('Building-: '+buildname+', count: '+buildingCount+', Sold Aount: '+SoldAmount+', AmountOwned: '+AmountOwned)

          x_axis = null;
          y_axis = null;

          if (x == "DateFrom"){
            x_axis = buildname;
            y_axis = SoldAmount;
            console.log('X is ==>', x)
          }
          else if(x == "Project"){
            if ($('#datepicker1').val()){
                x_axis = buildname;
                y_axis = buildingCount;
                console.log('X Project is ==>'+ x+ 'And x-axis is '+y_axis)
              } else{
                alert("Please Select date duration to Filter!")
              }

          }
          else if(x == "DateTo" && $('#sales_by_project_select').val()){
            x_axis = buildname;
            y_axis = SoldAmount;
            console.log('X Project is ==>'+ x+ 'And x-axis is '+y_axis)

          }else{
            alert('Please select a Project and Start Date!');
          }

          console.log('TYPE XX -'+ typeof(x), 'x= '+x_axis+'; y= '+y_axis)
          ///////
          // GraphDisplay(x_axis, y_axis);
          mainx_axis = x_axis;
          mainy_axis = y_axis;
          jQuery('.grider').empty();
          jQuery('.grider').append(jQuery('<div name="bar_graph" id="bar-div" class="bar_graph"> \
          <a class="btn-primary block mt-2 text-center" href="#feedback">Bar Graph</a>\
          <canvas id="bar-chart2" width="200" height="80"/><p/>\
          </div><p/>')) 
          GraphDynamicDisplay(x_axis, y_axis, "bar-chart2", "bar");
          console.log('Graph displayed For projects 2')
          ///////
          
        })
      }

     
      $('#datepicker2').change(function(){
         
        // RenderGraph("DateTo");
        if($('#datepicker1').val()){
            $('#is_sold_filter').prop('checked', false);
            $('#is_option_all').prop('checked', false);
            $('#is_unsold_filter').prop('checked', false);
            $('#is_reserved_filter').prop('checked', false);
            var xproject = $('#sales_by_project_select').val() ? $('#sales_by_project_select').val() : null;
            var xdatefrom = $('#datepicker1').val() ? $('#datepicker1').val() : null;
            var xdateto = $('#datepicker2').val() ? $('#datepicker2').val() : null;
            // var sales = $('#is_option_all').val() !== "All" ? "NoDatefilter" : "Sold";

            BuildingModel.call('dynamic_projects_rendering', [[0],xproject,xdatefrom,xdateto,"NoDatefilter"],
              {context: ''}).then(function (data) {
                var Buildings = [];
                var Building_Counter = 1;
                var x_axis = [];
                var y_axis = [];
                x_axis = data['list_buildings']
                y_axis = data['list_unsold']
                console.log('x axis', x_axis);
                  
                console.log('y axis',y_axis)
                ///////
                // GraphDisplay(x_axis, y_axis);
                mainx_axis = x_axis;
                mainy_axis = y_axis;
                jQuery('.grider').empty();
                jQuery('.grider').append(jQuery('<div name="bar_graph" id="bar-div" class="bar_graph"> \
                <a class="btn-primary block mt-2 text-center" href="#feedback">Bar Graph</a>\
                <canvas id="bar-chart2" width="200" height="80"/><p/>\
                </div><p/>')) 
                GraphDynamicDisplay(x_axis, y_axis, "bar-chart2", "bar");
                console.log('Graph displayed For projects 2')
                 
              });
            console.log('Date to selected')
        } else {
            alert("Please select Date From")
        }
             
      })

      $('#datepicker1').change(function(){
        // RenderGraph("DateFrom");
        console.log("Date start selected")
      })

      $('#is_option_all').change(function(){
        if ($(this).prop('checked')) {
            // DynamicMethod(null,null,null,null,null)
            $('#is_sold_filter').prop('checked', false);
            $('#is_unsold_filter').prop('checked', false);
            $('#is_reserved_filter').prop('checked', false);

            var xproject = $('#sales_by_project_select').val() ? $('#sales_by_project_select').val() : null;
            var xdatefrom = $('#datepicker1').val() ? $('#datepicker1').val() : null;
            var xdateto = $('#datepicker2').val() ? $('#datepicker2').val() : null;
            // var sales = $('#datepicker2').val() ? "NoDatefilter" : "All";
          console.log('HereX ==>  Date set for select project ' +xdatefrom+' and '+ xdateto+' For project: '+xproject);

            BuildingModel.call('dynamic_projects_rendering', [[0],xproject,xdatefrom,xdateto,"NoDatefilter"],
              {context: ''}).then(function (data) {
                var Buildings = [];
                var Building_Counter = 1;
                var x_axis = [];
                var y_axis = [];
                x_axis = data['list_buildings']
                y_axis = data['list_unsold']
                console.log('x axis', x_axis);
                  
                console.log('y axis',y_axis) 
                ///////
                // GraphDisplay(x_axis, y_axis);
                mainx_axis = x_axis;
                mainy_axis = y_axis;
                jQuery('.grider').empty();
                jQuery('.grider').append(jQuery('<div name="bar_graph" id="bar-div" class="bar_graph"> \
                <a class="btn-primary block mt-2 text-center" href="#feedback">Bar Graph</a>\
                <canvas id="bar-chart2" width="200" height="80"/><p/>\
                </div><p/>')) 
                GraphDynamicDisplay(x_axis, y_axis, "bar-chart2", "bar");
                console.log('Graph displayed For projects 2')
                ///////
                // var count_y = [];
                //   _.each(data, function(result){
                //   Buildings.push(result);
                  
                //   // console.log('DATA Found for Dynamic Building Rendering ==>', Buildings)
                //   x_axis.push(result);
                //   y_axis.push(Building_Counter);
                //   console.log('x axis', x_axis);
                //   console.log('y axis',y_axis) 
                //   Building_Counter = Building_Counter + 1;

                // });
                  //////
                  // GraphDisplay(x_axis, y_axis);
                  // console.log('Graph displayed for All')
                    ///////
              });
            console.log('All fired!!!')
             
        } 

      })

      $('#is_sold_filter').change(function(){
        if ($(this).prop('checked')) {
 
            $('#is_unsold_filter').prop('checked', false);
            $('#is_reserved_filter').prop('checked', false);
            $('#is_option_all').prop('checked', false);

            var xproject = $('#sales_by_project_select').val() ? $('#sales_by_project_select').val() : null;
            var xdatefrom = $('#datepicker1').val() ? $('#datepicker1').val() : null;
            var xdateto = $('#datepicker2').val() ? $('#datepicker2').val() : null;

            BuildingModel.call('dynamic_projects_rendering', [[0],xproject,xdatefrom,xdateto,"Sold"],
              {context: ''}).then(function (data) {
                var Buildings = [];
                var Building_Counter = 1;
                var x_axis = [];
                var y_axis = [];
                x_axis = data['list_buildings']
                y_axis = data['list_sold']
                console.log('x axis', x_axis);
                  
                console.log('y axis',y_axis) 
                ///////
                // GraphDisplay(x_axis, y_axis);
                mainx_axis = x_axis;
                mainy_axis = y_axis;
                jQuery('.grider').empty();
                jQuery('.grider').append(jQuery('<div name="bar_graph" id="bar-div" class="bar_graph"> \
                <a class="btn-primary block mt-2 text-center" href="#feedback">Bar Graph</a>\
                <canvas id="bar-chart2" width="200" height="80"/><p/>\
                </div><p/>')) 
                GraphDynamicDisplay(x_axis, y_axis, "bar-chart2", "bar");
                console.log('Graph displayed For projects 2')
                 
              });
            console.log('Sold')
             
        } 

      })

      $('#is_unsold_filter').change(function(){
        if ($(this).prop('checked')) {
            // DynamicMethod(null,null,null, "UnSold")
            $('#is_sold_filter').prop('checked', false);
            $('#is_reserved_filter').prop('checked', false);
            $('#is_option_all').prop('checked', false);
            var xproject = $('#sales_by_project_select').val() ? $('#sales_by_project_select').val() : null;
            var xdatefrom = $('#datepicker1').val() ? $('#datepicker1').val() : null;
            var xdateto = $('#datepicker2').val() ? $('#datepicker2').val() : null;
            console.log('Reserved ==>  Date set for select project ' +xdatefrom+' and '+ xdateto+' For project: '+xproject);

            BuildingModel.call('dynamic_projects_rendering', [[0],xproject,xdatefrom,xdateto, "UnSold"],
              {context: ''}).then(function (data) {
                 
                var x_axis = [];
                var y_axis = [];
                x_axis = data['list_buildings']
                y_axis = data['list_unsold']
                console.log('x axis', x_axis);
                  
                console.log('y axis',y_axis) 
                // GraphDisplay(x_axis, y_axis);
                mainx_axis = x_axis;
                mainy_axis = y_axis;
                jQuery('.grider').empty();
                jQuery('.grider').append(jQuery('<div name="bar_graph" id="bar-div" class="bar_graph"> \
                <a class="btn-primary block mt-2 text-center" href="#feedback">Bar Graph</a>\
                <canvas id="bar-chart2" width="200" height="80"/><p/>\
                </div><p/>')) 
                GraphDynamicDisplay(x_axis, y_axis, "bar-chart2", "bar");
                console.log('Graph displayed For projects 2')
                 
              });
              //
            console.log('UnSold')
             
        } 

      })

      $('#is_reserved_filter').change(function(){
        if ($(this).prop('checked')) {
            console.log('Yes Clicked')
            $('#is_sold_filter').prop('checked', false);
            $('#is_unsold_filter').prop('checked', false);
            $('#is_option_all').prop('checked', false);

            var xproject = $('#sales_by_project_select').val() ? $('#sales_by_project_select').val() : null;
            var xdatefrom = $('#datepicker1').val() ? $('#datepicker1').val() : null;
            var xdateto = $('#datepicker2').val() ? $('#datepicker2').val() : null;
            console.log('Reserved ==>  Date set for select project ' +xdatefrom+' and '+ xdateto+' For project: '+xproject);


            BuildingModel.call('dynamic_projects_rendering', [[0],xproject,xdatefrom,xdateto,"Reserved"],
              {context: ''}).then(function (data) {
                var x_axis = [];
                var y_axis = [];

                x_axis = data['list_buildings']
                y_axis = data['list_unsold']
                console.log('x axis', x_axis);
                  
                console.log('y axis',y_axis)
                // GraphDisplay(x_axis, y_axis);
                mainx_axis = x_axis;
                mainy_axis = y_axis;
                jQuery('.grider').empty();
                jQuery('.grider').append(jQuery('<div name="bar_graph" id="bar-div" class="bar_graph"> \
                <a class="btn-primary block mt-2 text-center" href="#feedback">Bar Graph</a>\
                <canvas id="bar-chart2" width="200" height="80"/><p/>\
                </div><p/>')) 
                GraphDynamicDisplay(x_axis, y_axis, "bar-chart2", "bar");
                console.log('Graph displayed For projects 2')
                ///////
                // var count_y = [];
                //   _.each(data, function(result){
                //   Buildings.push(result);
                  
                //   // console.log('DATA Found for Dynamic Building Rendering ==>', Buildings)
                //   x_axis.push(result);
                //   y_axis.push(Building_Counter);
                //   console.log('x axis', x_axis);
                //   console.log('y axis',y_axis) 
                //   Building_Counter = Building_Counter + 1;

                // });
                  //////
                  // GraphDisplay(x_axis, y_axis);
                  // console.log('Reserved Graph displayed')
                    ///////
              });
              //
            console.log('Reserved')
             
        } 

      })





    }
    
    var init = Init();
    // var StartRendering = StartDynamic();
  });

});

 