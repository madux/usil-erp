from odoo import http
from odoo.http import Controller, route, request

class displayGraph(http.Controller):

    @http.route('/graphs', auth="public", website=True)
    def plotGraph(self):
        property_obj = http.request.env['sale.order'].search([])
        count = 1
        count_list =[]
        sales_list = []
        for rec in property_obj:
            if rec.location_project:
                count_list.append(str(rec.location_project.name))
                sales_list.append(count)
                count +=1

        return http.request.render('property_sale.graph_template', 
        {
            'sales_x': count_list,
            'count_y' : sales_list
        })

    @http.route('/bireport', auth="public", website=True)
    def plotProjectGraph(self):
        project_name =[]
        project_remain =[]
        project_unit =[]
        project_sold =[]
        count_list =[]
        sales_list = []
        property_obj = http.request.env['property.report'].search([], limit=1)
        for rec in property_obj.mapped('project_ids'):
            project_unit.append(rec.total_unit)
            project_sold.append(rec.total_sold)
            project_remain.append(rec.total_remain)
            project_name.append(str(rec.name))
        return http.request.render('property_sale.bireport_template', {
            'measure_horizontal': project_name,
            'measure_vertical': project_sold,
        })

    @http.route('/bi-summary', auth="public", website=True)
    def SummaryChart(self):
        return http.request.render('property_sale.summary_page_view', {})
    
    @http.route('/filterdate', auth="public", type="http", website=True, csrf=False, )
    def datefiltered(self, datefrom=None, dateto=None, **kw):
        project_name =[]
        project_sold =[]
        orders = http.request.env['building.type.model'].search([('purchase_date', '>=', datefrom ),('purchase_date', '<=', dateto)], limit=1)
        for rec in orders:
            project_sold.append(rec.list_price)
            project_name.append(str(rec.name))
        return http.request.render('property_sale.bi_filtered_report', {
            'measure_horizontal': project_name,
            'measure_vertical': project_sold,
        })

    @http.route('/projects/params', type='json', website=True, auth="public", csrf=False)
    def project_param_data(self, proj, datefrm, dateto):
        buildings = http.request.env['building.type.model'].sudo().search([
            ('location_project.name', '<=', proj),
            ('purchase_date', '>=', datefrm),
            ('purchase_date', '<=', dateto),
            ])
        if buildings:
            return {
            'measure_horizontal_building_name': [projs.name for projs in buildings],
            'measure_vert_count': [nums + 1 for nums, ids in enumerate(buildings)],
            'measure_vert_amount': [amt.property_sale_order_id.amount_total for amt in buildings],
            'measure_vert_amount_owned': [amt.property_sale_order_id.outstanding for amt in buildings],
            'measure_vert_amount_paid': [amt.property_sale_order_id.amount_paid for amt in buildings],

            }
             

    # @http.route('/project/name', type='json', website=True, auth="public")
    # def projectname(self, proj_name, **kw):
    #     ''' Fetch the list of project
    #     '''
    #     proj_name = kw.get('input_data')
    #     list_proj = []
    #     projects = http.request.env['project.configs'].sudo().search([('name','=',proj_name)], limit=1)
    #     if projects:
    #         return {
    #             'm_horizontal': [projs.name for projs in projects],
    #             'm_vertical': [projs.total_sold for projs in projects]}
         
    # @http.route('/projects/ids', type='json', website=True, auth="user")
    # def projectIds(self, **kw):
    #     ''' Fetch the list of project
    #     '''
    #     list_proj = []
    #     projects = http.request.env['project.configs'].sudo().search([])
    #     if projects:
    #         return {
    #             'project_ids': [projs.name for projs in projects],
    #             # 'm_vertical': [projs.total_sold for projs in projects]
    #             }
    
    