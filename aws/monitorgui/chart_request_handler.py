from monitorgui import web

render = web.template.render('monitorgui/templates/')

urls = (
  "", "chart_request_handler",
)

class chart_request_handler:
     def GET(self):
        user_data = web.input()
        return render.display_graph("/query?inst_id="+str(user_data.inst_id)+"&env="+str(user_data.env))
    

app_chart_request_handler = web.application(urls, locals())