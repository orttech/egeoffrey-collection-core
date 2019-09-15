

// login screen and gui initialization
class Login {
    constructor() {
        // draw login box
        $("#login_box").html('\
            <p class="login-box-msg">'+locale("login.welcome")+'</p>\
            <form id="login_form">\
                <div class="card card-primary">\
                    <div class="card-header with-border">\
                        <h3 class="card-title">'+locale("login.gateway")+'</h3>\
                        <div class="card-tools pull-right">\
                            <button type="button" class="btn btn-card-tool" data-widget="collapse"><i class="fa fa-minus"></i>\
                            </button>\
                        </div>\
                    </div>\
                    <div class="card-body">\
                        <div class="form-group has-feedback">\
                            <input type="input" class="form-control" placeholder="'+locale("login.gateway.hostname")+'" id="egeoffrey_gateway_hostname">\
                        </div>\
                        <div class="form-group has-feedback">\
                            <input type="input" class="form-control" placeholder="'+locale("login.gateway.port")+'" id="egeoffrey_gateway_port">\
                        </div>\
                        <div class="form-group has-feedback">\
                            <div class="checkbox icheck">\
                                <label>\
                                    <input type="checkbox" id="egeoffrey_gateway_ssl"> '+locale("login.gateway.ssl")+'\
                                </label>\
                            </div>\
                        </div>\
                    </div>\
                </div>\
                <div class="card card-primary">\
                    <div class="card-header with-border">\
                        <h3 class="card-title">'+locale("login.house")+'</h3>\
\
                        <div class="card-tools pull-right">\
                            <button type="button" class="btn btn-card-tool" data-widget="collapse"><i class="fa fa-minus"></i>\
                            </button>\
                        </div>\
                    </div>\
                    <div class="card-body">\
                        <div class="form-group has-feedback">\
                            <input type="input" class="form-control" placeholder="'+locale("login.house.id")+'" id="egeoffrey_id">\
                        </div>\
                        <div class="form-group has-feedback">\
                            <input type="password" class="form-control" placeholder="'+locale("login.house.passcode")+'" id="egeoffrey_passcode">\
                        </div>\
                    </div>\
                </div>\
                <div class="card card-primary">\
                    <div class="card-header with-border">\
                        <h3 class="card-title">'+locale("login.user")+'</h3>\
\
                        <div class="card-tools pull-right">\
                            <button type="button" class="btn btn-card-tool" data-widget="collapse"><i class="fa fa-minus"></i>\
                            </button>\
                        </div>\
                    </div>\
                    <div class="card-body">\
                        <div class="form-group has-feedback">\
                            <input type="input" class="form-control" placeholder="'+locale("login.user.username")+'" id="egeoffrey_username">\
                        </div>\
                        <div class="form-group has-feedback">\
                            <input type="password" class="form-control" placeholder="'+locale("login.user.password")+'" id="egeoffrey_password">\
                        </div>\
                    </div>\
                </div>\
                <center>\
                    <p class="text-red" id="login_error"></p>\
                </center>\
                <div class="form-group has-feedback">\
                    <div class="checkbox icheck">\
                        <label>\
                            <input type="checkbox" id="egeoffrey_remember_me" checked> '+locale("login.remember_me")+'\
                        </label>\
                    </div>\
                </div>\
                <div class="form-group has-feedback">\
                    <button type="button" class="btn btn-primary btn-block btn-flat" id="login_button">'+locale("login.login_button")+'</button>\
                </div>\
            </form>\
        ')
        // submit form on enter keypress
        $('#login_form :input').keypress(function (e) {
          if (e.which == 13) {
            $("#login_button").trigger("click")
            return false;
          }
        });
        // set to true when the login button is pressed
        var login_submit = false
        // setup checkboxes
        $(":checkbox").iCheck({
            checkboxClass: 'icheckbox_square-blue',
            radioClass: 'iradio_square-blue',
            increaseArea: '20%'
        });
        // configure login button
        $("#login_button").unbind().click(function(this_class) {
            return function() {
                // disable the login button
                $("#login_button").prop("disabled", true)
                $("#login_button").html(locale("login.connecting"))
                $("#login_error").html("")
                    // pull out the user's data and set the variables
                window.EGEOFFREY_GATEWAY_HOSTNAME = $("#egeoffrey_gateway_hostname").val()
                window.EGEOFFREY_GATEWAY_PORT = $("#egeoffrey_gateway_port").val()
                window.EGEOFFREY_GATEWAY_SSL = $("#egeoffrey_gateway_ssl").is(":checked") ? 1 : 0
                window.EGEOFFREY_ID = $("#egeoffrey_id").val()
                window.EGEOFFREY_PASSCODE = $("#egeoffrey_passcode").val()
                window.EGEOFFREY_USERNAME = $("#egeoffrey_username").val()
                window.EGEOFFREY_PASSWORD = $("#egeoffrey_password").val()
                window.EGEOFFREY_REMEMBER_ME = $("#egeoffrey_remember_me").is(":checked") ? 1 : 0
                    // create a new instance of the gui and run it
                window.gui = new Gui("gui", EGEOFFREY_USERNAME + "_" + this_class.generate_session_id())
                window.gui.run()
                login_submit = true
            };
        }(this));
        // periodically check if the connection is established, otherwise show login page
        var watchdog = setInterval(function() {
            $("#login_button").prop("disabled", false)
            $("#login_button").html(locale("login.login_button"))
            var login_screen = $('#login').is(':visible');
            // when the login screen is shown
            if (login_screen) {
                // check if connected and if so hide the login screen
                if (window.gui.connected) {
                    // connected
                    $("#login_error").html("")
                        // remember user credentials if requested
                    if ($("#egeoffrey_remember_me").is(":checked")) {
                        localStorage.setItem("EGEOFFREY_GATEWAY_HOSTNAME", window.EGEOFFREY_GATEWAY_HOSTNAME)
                        localStorage.setItem("EGEOFFREY_GATEWAY_PORT", window.EGEOFFREY_GATEWAY_PORT)
                        localStorage.setItem("EGEOFFREY_GATEWAY_SSL", window.EGEOFFREY_GATEWAY_SSL)
                        localStorage.setItem("EGEOFFREY_ID", window.EGEOFFREY_ID)
                        localStorage.setItem("EGEOFFREY_PASSCODE", window.EGEOFFREY_PASSCODE)
                        localStorage.setItem("EGEOFFREY_USERNAME", window.EGEOFFREY_USERNAME)
                        localStorage.setItem("EGEOFFREY_PASSWORD", window.EGEOFFREY_PASSWORD)
                        localStorage.setItem("EGEOFFREY_REMEMBER_ME", window.EGEOFFREY_REMEMBER_ME)
                    } else localStorage.clear()
                    $("#login").modal("hide")
                    login_submit = false
                } else {
                    if (login_submit) $("#login_error").html(locale("login.login_error"))
                    login_submit = false
                }
            }
            // already logged in, ensure we are still connected
            else {
                if (!window.gui.connected) {
                    // not connected, stop the current instance of the gui from connecting
                    window.gui.join()
                    // set login information from previous settings
                    $("#egeoffrey_gateway_hostname").val(gui.gateway_hostname)
                    $("#egeoffrey_gateway_port").val(gui.gateway_port)
                    if (gui.gateway_ssl) $("#egeoffrey_gateway_ssl").iCheck('check')
                    else $("#egeoffrey_gateway_ssl").iCheck('uncheck')
                    $("#egeoffrey_id").val(gui.house_id)
                    $("#egeoffrey_passcode").val(gui.house_passcode)
                    $("#egeoffrey_username").val(gui.username)
                    $("#egeoffrey_password").val(gui.password)
                        // show up the login screen
                    $("#login").modal()
                }
            }
        }, 2000);
    }
    
    // generate a random session_id
    generate_session_id() {
        var min = 1;
        var max = 100000;
        return Math.floor(Math.random() * (+max - +min)) + +min;
    }
    
    // load the gui
    load() {
        // restore user credentials 
        if (localStorage.getItem("EGEOFFREY_GATEWAY_HOSTNAME") != null) window.EGEOFFREY_GATEWAY_HOSTNAME = localStorage.getItem("EGEOFFREY_GATEWAY_HOSTNAME")
        if (localStorage.getItem("EGEOFFREY_GATEWAY_PORT") != null) window.EGEOFFREY_GATEWAY_PORT = localStorage.getItem("EGEOFFREY_GATEWAY_PORT")
        if (localStorage.getItem("EGEOFFREY_GATEWAY_SSL") != null) window.EGEOFFREY_GATEWAY_SSL = parseInt(localStorage.getItem("EGEOFFREY_GATEWAY_SSL"))
        if (localStorage.getItem("EGEOFFREY_ID") != null) window.EGEOFFREY_ID = localStorage.getItem("EGEOFFREY_ID")
        if (localStorage.getItem("EGEOFFREY_PASSCODE") != null) window.EGEOFFREY_PASSCODE = localStorage.getItem("EGEOFFREY_PASSCODE")
        if (localStorage.getItem("EGEOFFREY_USERNAME") != null) window.EGEOFFREY_USERNAME = localStorage.getItem("EGEOFFREY_USERNAME")
        if (localStorage.getItem("EGEOFFREY_PASSWORD") != null) window.EGEOFFREY_PASSWORD = localStorage.getItem("EGEOFFREY_PASSWORD")
        if (localStorage.getItem("EGEOFFREY_REMEMBER_ME") != null) window.EGEOFFREY_REMEMBER_ME = parseInt(localStorage.getItem("EGEOFFREY_REMEMBER_ME"))
        // create a gui and start it
        window.gui = new Gui("gui", "guest_" + this.generate_session_id())
        window.gui.run()
    }
}