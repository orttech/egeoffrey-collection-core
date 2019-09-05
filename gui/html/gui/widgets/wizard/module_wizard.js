// module wizard widget
class Module_wizard extends Widget {
    constructor(id, widget) {
        super(id, widget)
        // the module we are editing the configuration for
        this.module_id = null
        // if waiting for the manifest
        this.waiting_manifest = false
        // if waiting for the configuration
        this.waiting_configuration = false
    }
    
    // draw the widget's content
    draw() {
        // extract requested module_id name from URL
        if (location.hash.includes("=")) {
            var request = location.hash.split("=")
            this.module_id = request[1]
        }
        // clear up the modal
        $("#wizard_body").html("")
        $("#wizard_title").html("Module Configuration")
        // show the modal
        $("#wizard").modal()
        // build the form
        $("#wizard_body").append('\
            <form method="POST" role="form" id="'+this.id+'_form" class="needs-validation" novalidate>\
                <ul class="nav nav-tabs" id="'+this.id+'_tabs" role="tablist">\
                    <li class="nav-item">\
                        <a class="nav-link active" id="'+this.id+'_tab_configuration" data-toggle="pill" href="#'+this.id+'_tab_configuration_content" role="tab" aria-controls="'+this.id+'_tab_configuration_content" aria-selected="true">'+this.module_id+'</a>\
                    </li>\
                    <li class="nav-item">\
                        <a class="nav-link" id="'+this.id+'_tab_schema" data-toggle="pill" href="#'+this.id+'_tab_schema_content"  role="tab" aria-controls="'+this.id+'_tab_schema_content" aria-selected="false">Configuration Schema</a>\
                    </li>\
                </ul>\
                <div class="tab-content">\
                    <div class="tab-pane fade show active" id="'+this.id+'_tab_configuration_content" role="tabpanel" aria-labelledby="'+this.id+'_tab_configuration">\
                    </div>\
                    <div class="tab-pane fade" id="'+this.id+'_tab_schema_content" role="tabpanel" aria-labelledby="'+this.id+'_tab_schema">\
                        <div class="form-group">\
                            <label>Configuration Schema Version*</label>\
                            <input type="text" id="'+this.id+'_schema" class="form-control" placeholder="the version of the configuration schema" required>\
                        </div>\
                    </div>\
                </div>\
            </form>\
        ')
        // add link to advanced configuration
        var link = this.module_id == null ? "__new__" : this.module_id
        $("#wizard_body").append('<a id="'+this.id+'_advanced_editor" class="float-right text-primary">Advanced Editor</a>')
        $("#"+this.id+"_advanced_editor").unbind().click(function(this_class) {
            return function () {
                $('#wizard').unbind('hidden.bs.modal')
                $("#wizard").modal("hide")
                gui.unload_page()
                window.location.hash = "#__configuration="+link 
            };
        }(this));
        // what to do when the form is submitted
        var id = this.id
        var this_class = this
        $('#'+this.id+'_form').on('submit', function (e) {
            // form is validated
            if ($('#'+this_class.id+'_form')[0].checkValidity()) {
                // build up the configuration file
                var configuration = {}
                $("#"+this_class.id+"_form :input").each(function(e){
                    var item = this.id.replace(this_class.id+"_module_", "")
                    var value = this.value
                    if (value != null && value != "") configuration[item] = $.isNumeric(value) ? parseFloat(value) : value
                });
                // save new/updated configuration
                var message = new Message(gui)
                message.recipient = "controller/config"
                message.command = "SAVE"
                message.args = this_class.module_id
                message.config_schema = gui.supported_sensors_config_schema
                message.set_data(configuration)
                gui.send(message)
                // close the modal
                $("#wizard").modal("hide")
                gui.notify("success","Configuration of module "+this_class.module_id+" saved successfully")
                return false
            }
            else {
                e.preventDefault();
                e.stopPropagation();
            }
            $('#'+this_class.id+'_form').addClass("was-validated")
        })
        // configure submit button
        $('#wizard_save').unbind().click(function(this_class) {
            return function () {
                $("#"+this_class.id+"_form").submit()
            };
        }(this))
        // what to do when the modal is closed
        $('#wizard').one('hidden.bs.modal', function () {
            gui.unload_page()
            window.history.back()
        })
        // identify the watchdog managing this module
        var message = new Message(gui)
        message.recipient = "*/*"
        message.command = "DISCOVER"
        message.args = this.module_id
        this.send(message)
    }
    
    // receive data and load it into the widget
    on_message(message) {
        // discovery response from the watchdog managing the requested module
        if (message.command == "DISCOVER") {
            // now we need the manifest published by this watchdog to retrieve the module's configuration schema
            this.add_broadcast_listener(message.sender, "MANIFEST", "#")
            this.waiting_manifest = true
        }
        // receive manifest from watchdog
        if (message.command == "MANIFEST") {
            if (! this.waiting_manifest) return
            var manifest = message.get_data()
            if (manifest["manifest_schema"] != gui.supported_manifest_schema) return
            // for each module of the package
            var found = false
            for (var module_object of manifest["modules"]) {
                for (var module in module_object) {
                    if (module != this.module_id) continue
                    if (! gui.is_valid_configuration(["module_configuration"], module_object[module])) continue
                    // build up the form
                    for (var configuration of module_object[module]["module_configuration"]) {
                        var input = ""
                        var required = "required" in configuration && configuration["required"] ? "required" : ""
                        var required_flag = required != "" ? "*" : ""
                        var options_html = ""
                        if (required == "") options_html = options_html+'<option value=""></option>'
                        // draw a text input
                        if (["int", "float", "string", "password"].includes(configuration["format"])) {
                            var placeholder = "placeholder" in configuration ? "e.g. "+configuration["placeholder"] : ""
                            var type = configuration["format"] == "password" ? "password" : "text"
                            input = '\
                                <div class="form-group">\
                                    <label>'+configuration["description"]+required_flag+'</label>\
                                    <input type="'+type+'" id="'+this.id+'_module_'+configuration["name"]+'" name="'+configuration["name"]+'" class="form-control" placeholder="'+placeholder+'" '+required+'>\
                                </div>'
                        }
                        // draw a checkbox
                        else if (configuration["format"] == "checkbox") {
                            input = '\
                                <div class="form-group">\
                                    <label>'+configuration["description"]+required_flag+'</label>\
                                    <input type="checkbox" class="form-check-input" id="'+this.id+'_module_'+configuration["name"]+'">\
                                </div>'
                        }
                        // draw a select input
                        else if (configuration["format"].includes("|")) {
                            var options = configuration["format"].split("|")
                            for (var option of options) options_html = options_html+'<option value="'+option+'">'+option+'</option>'
                            input = '\
                                <div class="form-group">\
                                    <label>'+configuration["description"]+required_flag+'</label>\
                                    <select id="'+this.id+'_module_'+configuration["name"]+'" name="'+configuration["name"]+'" class="form-control" '+required+'>'+options_html+'</select>\
                                </div>'
                        }
                        $('#'+this.id+'_tab_configuration_content').append(input)
                    }
                    // request the module's configuration
                    this.add_configuration_listener(this.module_id, "+")
                    this.waiting_configuration = true
                    found = true
                    break
                }
            }
            this.waiting_manifest = false
            // the manifest does not contain any information regarding this module, exiting
            if (! found) {
                $("#wizard").modal("hide")
                gui.notify("warning","Configuration schema of module "+this.module_id+" not available")
            }
        }
    }
    
    // receive configuration
    on_configuration(message) {
        // receive module's configuration
        if (message.args == this.module_id) {
            if (! this.waiting_configuration) return
            $("#"+this.id+"_schema").val(message.config_schema)
            $("#"+this.id+"_tab_schema").parent("li").addClass("d-none")
            var data = message.get_data()
            // populate the form
            for (var configuration in data) {
                var value = data[configuration]
                // populate checkbox
                if ($("#"+this.id+"_module_"+configuration).is(':checkbox')) {
                    $("#"+this.id+"_module_"+configuration).prop("checked", value)
                }
                // populate other inputs
                else {
                    $("#"+this.id+"_module_"+configuration).val(value)
                }
            }
            this.waiting_configuration = false
        }
    }
}