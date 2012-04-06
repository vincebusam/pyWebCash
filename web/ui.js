var apiurl = "api.py";
var loadedtransactions = [];
var accountsearches = [ {} ];
var showing = -1;
var showtrans = {};
var editedfields = []
var limit = 25;
var skip = 0;
var query = accountsearches[0];
var sessioncheckinterval = null;
var categories = {};
var allcategories = [];
var centers = [];
var tags = [];
var linkparent = "";
var linkchildren = [];

// "nice" jQueryUI popup message
function showerror(err) {
  $("#errormsg").text(err);
  $("#errormsg").dialog("open");
}

// After login, reset everything
function loginsuccess() {
  $("#login").hide();
  $("#searchoptions").show();
  $("#linktransactions").show();
  $("#linktransactions").width($("#searchoptions").width())
  $("#searchoptions .searchoption").each(function () { $(this).val(""); });
  $("#searchoptions .queryoption").each(function () { $(this).val(""); });
  clearlink();
  loadedtransactions = [];
  showing = -1;
  limit = 25;
  skip = 0;
  loadaccounts();
  // Get user's categories and configure everywhere
  $.ajax({
    type: "POST",
    url: apiurl,
    data: { "action": "getcategories" },
    success: function (data) {
      categories = data;
      allcategories = []
      for (cat in categories) {
        allcategories.push(cat);
        allcategories = allcategories.concat(categories[cat]);
      }
      allcategories.sort();
      keys = Object.keys(categories);
      keys.sort();
      $(".category").autocomplete({
        source: keys,
        delay: 50,
        minLength: 0,
        select: function(event, ui) {
          if ($(this).hasClass("transdataval")) {
            $("#transactiondetail .savebutton").button("enable");
            if (editedfields.indexOf("category") == -1)
              editedfields.push("category");
          }
          $(this).parent().children(".subcategory").autocomplete("option", "source", categories[ui.item.value]);
        }
      });
      $(".subcategory").autocomplete({
        source: allcategories,
        delay: 50,
        minLength: 0,
        select: function(event, ui) {
          if ($(this).hasClass("transdataval")) {
            if (editedfields.indexOf("subcategory") == -1)
              editedfields.push("subcategory");
            $("#transactiondetail .savebutton").button("enable");
          }
          catval = $(this).parent().children(".category").val();
          if ((catval == "") || (categories[catval].indexOf(ui.item.value) == -1)) {
            for (cat in categories) {
              if (categories[cat].indexOf(ui.item.value) != -1) {
                $(this).parent().children(".category").val(cat);
                if ($(this).hasClass("transdataval")) {
                  if (editedfields.indexOf("category") == -1)
                    editedfields.push("category");
                  $("#transactiondetail .savebutton").button("enable");
                }
                break;
              }
            }
          }
        }
      });
    },
    error: function () {
      showerr("Error loading categories!");
    }
  });
  // Get user's cost centers, load up elements.
  $.ajax({
    type: "POST",
    url: apiurl,
    data: { "action": "getcenters" },
    success: function(data) {
      centers = data;
      $(".centersel").each(function() {
        $(this).html("");
        $(this).append("<option value=''>All</option>");
        for (i = 0; i<centers.length; i++) {
          $(this).append("<option value='"+centers[i]+"'>"+centers[i]+"</option>");
        }
      });
    },
    error: function() {
      showerr("Error loading cost centers!");
    }
  });
  $.ajax({
    type: "POST",
    url: apiurl,
    data: { "action": "gettags" },
    success: function(data) {
      tags = data;
      tags.sort();
      $("#tagslist").html("");
      for (t in tags)
        $("#tagslist").append("<li>"+tags[t]+"</li>");
      $("#tagslist").selectable({
        selected: function(event, ui) {
            if (editedfields.indexOf("tags") == -1)
                editedfields.push("tags");
        },
        unselected: function(event, ui) {
            if (editedfields.indexOf("tags") == -1)
                editedfields.push("tags");
        }
      });
      $("#tagslist li").addClass("ui-widget-content");
    }
  });

  // Every minute, make sure session is still good.  Logout if bad.
  if (!sessioncheckinterval)
    sessioncheckinterval = setInterval(checksession, 60000);
}

// Clear everything, then check if we have a good session.
function clearpage() {
  $("#login").hide();
  $("#transactions").hide();
  $("#transactiondetail").dialog("close");
  $("#accounts").hide();
  $("#errormsg").hide();
  $("#searchoptions").hide();
  $("#newaccount").hide();
  $("#tagselect").hide();
  $("#linktransactions").hide();
  $("#username").val("");
  $("#password").val("");
  if (sessioncheckinterval) {
    clearInterval(sessioncheckinterval);
    sessioncheckinterval = null;
  }

  $.ajax({
    type: "POST",
    url: apiurl,
    data: { "action": "checklogin" },
    success: function(data) {
      if (data) {
        loginsuccess();
      } else {
        $("#login").show();
        $("#login").center();
        $("#username").focus();
      }
    },
    error: function() {
      $("#login").show();
      $("#login").center();
      $("#username").focus();
    }
  });
}

// Clear page if our session is bad.
function checksession() {
  $.ajax({
    type: "POST",
    url: apiurl,
    data: { "action": "checklogin" },
    success: function(data) {
      if (data) {
      } else {
        clearpage();
      }
    },
    error: function() {
      clearpage();
    }
  });
}

// Convert amount in positive/negative cents to human-readable format
function decoratedollar() {
  if ($(this).text().substring(0,1) == "$")
    return;
  amount = parseInt($(this).text());
  if (amount > 0)
    $(this).addClass("posnum");
  else
    $(this).removeClass("posnum");
  $(this).text("$"+Math.abs(amount/100).toFixed(2));
}

// Get accounts and balances, load up table and search options
function loadaccounts() {
  $.ajax({
    type: "POST",
    url: apiurl,
    data: { "action": "accounts" },
    success: function(data) {
      accountsearches = accountsearches.slice(0,1);
      $("#accounts > #bankaccounts").html("");
      for (i in data) {
        for (j in data[i]["subaccounts"]) {
          newaccount = "<div class='account useraccount' id='account"+accountsearches.length+"'>";
          newaccount += "<span class='accountname'>"+data[i]["name"]+"</span> / ";
          newaccount += "<span class='subname'>"+data[i]["subaccounts"][j]["name"]+"</span>";
          newaccount += "<div class='dollar accountbalance'>"+data[i]["subaccounts"][j]["amount"]+"</div>";
          newaccount += "<div class='accountupdate'>"+data[i]["subaccounts"][j]["date"]+"</div>";
          newaccount += "</div>";
          $("#accounts > #bankaccounts").append(newaccount);
          accountsearches.push({"account":data[i]["name"], "subaccount": data[i]["subaccounts"][j]["name"]});
        }
      }
      $(".dollar").each(decoratedollar);
      $(".account").click(function() {
        skip = 0;
        query = accountsearches[parseInt($(this).attr("id").substring(7))];
        $(".account").removeClass("ui-state-active");
        $(this).addClass("ui-state-active");
        loadtransactions();
      });
      $("#accounts").show();
      $("#account0").addClass("ui-state-active");
      query = accountsearches[0];
      loadtransactions();
    },
    error: function() {
      showerror("Error loading accounts");
    }
  });
}

// Store our saved fields for this transaction
function savetransaction() {
  if (editedfields.length > 0) {
    updatejson = new Object();
    for (f in editedfields) {
      newval = $("#transactiondetail #"+editedfields[f]).val();
      if (newval == "")
        newval = $("#transactiondetail #"+editedfields[f]).text();
      updatejson[editedfields[f]] = newval;
    }
    if (editedfields.indexOf("amount") != -1) {
      newamount = $("#transactiondetail #amount").text().replace("$","").replace(",","");
      if (newamount.indexOf(".") == -1) {
        newamount += ".00";
      } else if (newamount.indexOf(".") != (newamount.length-3)) {
        showerror("Bad amount");
        return;
      }
      newamount = newamount.replace(".","");
      if (showtrans["amount"] > 0)
        updatejson["amount"] = parseInt(newamount);
      else
        updatejson["amount"] = -parseInt(newamount);
    }
    if (editedfields.indexOf("tags") != -1) {
        updatejson["tags"] = showtrans["tags"];
    }
    $.ajax({
      type: "POST",
      url: apiurl,
      data: { "action": "updatetransaction", "id": showtrans["id"], "data" : JSON.stringify(updatejson) },
      success: function(data) {
        if (data) {
          showtransaction(showing);
          loadtransactions();
        } else {
          showerror("Error saving transaction");
        }
      },
      error: function() {
        showerror("HTTP Error saving transaction");
      }
    });
  }
}

// Show transaction detail, either index of loadedtransactions array, or object of a transaction.
function showtransaction(t) {
  if (typeof(t) == "number") {
    if (showing == t) {
      $("#transactiondetail").dialog("close");
      showing = -1;
      return;
    }
    showing = t;
    showtrans = loadedtransactions[t];
  } else {
    showtrans = t;
  }
  editedfields = [];
  $("#transactiondetail #save").button("disable");
  $("#transactiondetail #saveclose").button("enable");
  $("#transactiondetail > #file").hide();
  $("#transactiondetail .transdata").each(function () {
    name = $(this).attr("id");
    $(this).text("");
    if (showtrans[name] != undefined)
      $(this).text(showtrans[name]);
  });
  $("#transactiondetail .transdataval").each(function () {
    name = $(this).attr("id");
    $(this).val("");
    if (showtrans[name] != undefined)
      $(this).val(showtrans[name]);
  });
  $("#transactiondetail > #attr").html("");
  for (key in showtrans) {
    if ((key.indexOf("attr_") == 0) && (showtrans[key] != "")) {
      $("#transactiondetail > #attr").append(key.substr(5) + ": " + showtrans[key] + "<br>");
    }
  }
  if (showtrans["file"] != undefined) {
    $("#transactiondetail > #file").attr("src",apiurl+"?image="+showtrans["id"]);
    $("#transactiondetail > #file").show();
  }
  $(".dollar").each(decoratedollar);
  if (categories[showtrans["category"]] != undefined)
    $("#transactiondetail #subcategory").autocomplete("option", "source", categories[showtrans["category"]]);
  else
    $("#transactiondetail #subcategory").autocomplete("option", "source", allcategories);
  $("#transactiondetail #linked").html("");
  if (showtrans["parent"] != undefined) {
    $("#transactiondetail #linked").append("Linked Transactions:<br>");
    $("#transactiondetail #linked").append("<a href='#' class='translink'>"+showtrans["parent"]+"</a><br>");
  }
  if (showtrans["children"] != undefined) {
    $("#transactiondetail #linked").append("Linked Transactions:<br>");
    for (i=0; i<showtrans["children"].length; i++)
      $("#transactiondetail #linked").append("<a href='#' class='translink'>"+showtrans["children"][i]+"</a><br>");
  }
  $("#transactiondetail #tags").html("");
  if (showtrans["tags"] != undefined) {
    for (var tag in showtrans["tags"])
      $("#transactiondetail #tags").append(showtrans["tags"][tag] + " ");
  }
  $(".translink").click(function (event) {
    event.preventDefault();
    $.ajax({
      type: "POST",
      url: apiurl,
      data: { "action": "search", "query": JSON.stringify({"id": "$eq:" + $(this).text()}) },
      success: function(data) {
        if (data && data.length) {
          showtransaction(data[0]);
        } else {
          showerror("Bad transaction data");
        }
      },
      error: function(data) {
        showerror("Error getting transaction");
      }
    });
  });
  $("#transactiondetail").dialog("open");
}

// Search, load transactions to main table
function loadtransactions() {
  // hack to duplicate the existing query
  transquery = JSON.parse(JSON.stringify(query))
  for (i=0; i<$("#searchoptions .queryoption").length; i++) {
    if ($("#searchoptions .queryoption").eq(i).val())
      transquery[$("#searchoptions .queryoption").eq(i).attr("id")] = $("#searchoptions .queryoption").eq(i).val()
  }
  postdata = { "action": "search", "limit": limit, "skip": skip, "query": JSON.stringify(transquery) }
  for (i=0; i<$("#searchoptions .searchoption").length; i++) {
    if ($("#searchoptions .searchoption").eq(i).val() != "")
      postdata[$("#searchoptions .searchoption").eq(i).attr("id")] = $("#searchoptions .searchoption").eq(i).val()
  }
  $.ajax({
    type: "POST",
    url: apiurl,
    data: postdata,
    success: function(data) {
      total = 0;
      loadedtransactions = data;
      for (t=0; t<data.length; t++) {
        if ($("#transtablebody > #trans"+t).length == 0) {
          $("#transtablebody").append("<tr class='transaction' id='trans"+t+"'>"+
                                      "<td class='date'></td>"+
                                      "<td class='description'></td>"+
                                      "<td class='category'></td>"+
                                      "<td class='centertd'></td>"+
                                      "<td class='dollar'></td>"+
                                      "<td><button class='close'>Close</button></tr>");
          $("#trans"+t).click(function() {
            showtransaction(parseInt($(this).attr("id").substring(5)));
          });
          $("#trans"+t+" .close").button();
          $("#trans"+t+" .close").click(function() {
            transid = parseInt($(this).parent().parent().attr("id").substring(5));
            $.ajax({
              type: "POST",
              url: apiurl,
              data: { "action": "updatetransaction", "id": loadedtransactions[transid]["id"], "data" : JSON.stringify({"state": "closed"}) },
              context: this,
              success: function(data) {
                if (data) {
                  $(this).button("disable");
                  if (($("#searchoptions #state").val() != "") && ($("#searchoptions #state").val() != "closed"))
                    $(this).parent().parent().hide(200);
                } else
                  showerror("Error closing transaction");
              },
              error: function(data) {
                showerror("HTTP error closing transaction");
              }
            });
            return false;
          });
        }
        $("#transtablebody > #trans"+t+" .date").text(data[t]["date"]);
        $("#transtablebody > #trans"+t+" .description").text(data[t]["desc"]);
        $("#transtablebody > #trans"+t+" .dollar").text(data[t]["amount"]);
        $("#transtablebody > #trans"+t+" .centertd").text(data[t]["center"]);
        $("#transtablebody > #trans"+t+" .category").text("");
        if (data[t]["subcategory"] != undefined)
          $("#transtablebody > #trans"+t+" .category").text(data[t]["subcategory"]);
        else if (data[t]["category"] != undefined)
          $("#transtablebody > #trans"+t+" .category").text(data[t]["category"]);
        if (data[t]["state"] != "closed")
          $("#trans"+t+" .close").button("enable");
        else
          $("#trans"+t+" .close").button("disable");
        $("#transtablebody > #trans"+t).show();
        total += data[t]["amount"];
      }
      for (t=data.length; $("#transtablebody > #trans"+t).length > 0; t++)
        $("#transtablebody > #trans"+t).remove();
      $("#transactionsum").text(total);
      $(".dollar").each(decoratedollar);
      $("#transtablebody td").addClass("ui-widget-content");
      $("#transtablebody td").removeClass("ui-state-hover");
      $("#transtablebody button").removeClass("ui-state-hover");
      $("#transtablebody tr").hover(
        function() {
          $(this).children("td").addClass("ui-state-hover");
        },
        function() {
          $(this).children("td").removeClass("ui-state-hover");
        }
      );
      $("#transtablebody tr").draggable({
        revert: true,
        helper: "clone"
      });
      $("#transactions").show();
      $("#transtable").width($("#searchoptions").offset().left-$("#transtable").offset().left-5);
    },
    error: function() {
      showerror("Transaction loading error");
    }
  });
}

function clearlink() {
    linkparent = "";
    linkchildren = [];
    $("#linktransactions div").html("");
}

$(document).ready(function () {
  $('[contenteditable]').live('focus', function() {
    var $this = $(this);
    $this.data('before', $this.text());
      return $this;
  }).live('blur keyup paste', function() {
    var $this = $(this);
    if ($this.data('before') !== $this.text()) {
      $this.data('before', $this.text());
      if (editedfields.indexOf($(this).attr("id")) == -1) {
        editedfields.push($(this).attr("id"));
        $("#transactiondetail .savebutton").button("enable");
      }
    }
    return $this;
  });

  $("#transactiondetail .savebutton").button();
  $("#transactiondetail #save").click(savetransaction);
  $("#transactiondetail #saveclose").click(function() {
    $("#transactiondetail #state").val("closed")
    editedfields.push("state");
    savetransaction();
  });
  $("#transactiondetail > #dateselect").datepicker({
    dateFormat: "yy-mm-dd",
    altField: "#transactiondetail > #date",
    onSelect: function(dateText, inst) {
      $("#transactiondetail > #date").text(dateText);
      if (editedfields.indexOf("date") == -1) {
        editedfields.push("date");
        $("#transactiondetail .savebutton").button("enable");
      }
    }
  });
  $("#transactiondetail > #date").click(function() {
    $("#transactiondetail > #dateselect").datepicker("show");
  });
  $("#transactiondetail select").change(function () {
    if (editedfields.indexOf($(this).attr("id")) == -1) {
      editedfields.push($(this).attr("id"));
      $("#transactiondetail .savebutton").button("enable");
    }
    if (($(this).attr("id") == "state") && ($(this).val() != "closed"))
      $("#transactiondetail #saveclose").button("disable");
  });
  $("#transactiondetail #addtag").button({
    icons: {
      primary: "ui-icon-circle-plus"
    },
    text: false
  });
  $("#transactiondetail #addtag").click(function () {
    $("#tagselect").show();
    $("#tagselect").center();
    $("#tagselect ol").removeClass("ui-selected");
    if (showtrans["tags"] != undefined)
      $("#tagselect ol").each(function () {
        if (showtrans["tags"].indexOf($(this).text()) != -1)
          $(this).addClass("ui-selected");
      });
  });
  $("#tagselect button").button();
  $("#tagselect button").click(function () {
    showtrans["tags"] = [];
    $("#transactiondetail #tags").html("");
    $("#tagselect ol .ui-selected").each(function () {
        showtrans["tags"].push($(this).text());
        $("#transactiondetail #tags").append($(this).text() + " ");
        if (editedfields.indexOf("tags") == -1)
            editedfields.push("tags");
        $("#transactiondetail .savebutton").button("enable");
    });
    $("#tagselect").hide();
  });
  $("#transactiondetail").dialog({
    modal: true,
    autoOpen: false,
    title: "Edit Transaction",
    minWidth: 600,
    close: function() {
      showing = -1;
    }
  });

  $("#searchoptions .date").datepicker({
    dateFormat: "yy-mm-dd",
    onClose: function(dateText, inst) {
      loadtransactions();
    }
  });
  
  $("#searchoptions #center").change(function() {
    loadtransactions();
  });
  
  $("#searchoptions #executesearch").button();
  $("#searchoptions #executesearch").click(function () {
    skip = 0;
    loadtransactions();
  });
  
  $("#searchoptions #clearsearch").button();
  $("#searchoptions #clearsearch").click(function () {
    $("#searchoptions .searchoption").each(function () { $(this).val(""); });
    $("#searchoptions .queryoption").each(function () { $(this).val(""); });
    loadtransactions();
  });

  $("#errormsg").dialog({
    modal: true,
    autoOpen: false,
    title: "Error",
    minWidth: 250,
    buttons: {
      Ok: function() {
        $(this).dialog("close");
      }
    }
  });

  $(".limit").click(function(event) {
    event.preventDefault();
    if ($(this).text() == "all")
      limit = Number.MAX_VALUE;
    else
      limit = parseInt($(this).text());
    loadtransactions();
  });
  
  $(".page").click(function(event) {
    event.preventDefault();
    if ($(this).html() == "&lt;&lt;") {
      if (skip == 0)
        return;
      skip -= limit;
      if (skip < 0)
        skip = 0;
      loadtransactions();
    } else {
      if (loadedtransactions.length < limit)
        return;
      skip += limit;
      loadtransactions();
    }
  });

  $("#logout").click(function(event) {
    event.preventDefault();
    $.ajax({
      type: "POST",
      url: apiurl,
      data: { "action": "logout" },
      success: function() {
        clearpage();
      },
      error: function() {
        clearpage();
      }
    });
  });

  $("#loginsubmit").click(function () {
    $("#loginform").submit();
  });

  $("#loginform").keypress(function (e) {
    if ((e.which && e.which == 13) || (e.keyCode && e.keyCode == 13)) {
        $("#loginform").submit();
        return false;
    } else {
        return true;
    }
  });

  $("#loginform").submit(function () {
    $.ajax({
      type: "POST",
      url: apiurl,
      data: { "action": "login", "username": $("#username").val(), "password": $("#password").val() },
      success: function(data) {
        if (data) {
          loginsuccess();
        } else {
          showerror("Login Failed");
        }
      },
      error: function() {
        showerror("Login Error");
      }
    });
  });

  $("#newuser").click(function () {
    $.ajax({
      type: "POST",
      url: apiurl,
      data: { "action": "newuser", "username": $("#username").val(), "password": $("#password").val() },
      success: function(data) {
        if (data) {
          $("#loginsubmit").click();
        } else {
          showerror("Username already exists");
        }
      },
      error: function() {
        showerror("Error making new user");
      }
    });
  });

  $("#newaccount").dialog({
    modal: true,
    autoOpen: false,
    title: "Add/Edit Account"
  });

  $("#addaccount").click(function (event) {
    event.preventDefault();
    $.ajax({
      type: "POST",
      url: apiurl,
      data: { "action": "getbanks" },
      success: function(data) {
        newhtml = "<option value=''>Select a bank</option>";
        for (i=0; i<data.length; i++)
          newhtml += "<option value='"+data[i]+"'>"+data[i]+"</option>";
        $("#newaccount #bankname").html(newhtml);
      }
    });
    $("#newaccount > #createaccount").button("disable");
    $("#newaccount input").each(function() {
      $(this).val("");
    });
    $("#newaccount").dialog("open");
  });
  
  $("#newaccount .required").keyup(function () {
    ready = true;
    for (var i=0; i<$("#newaccount .required").length; i++) {
      if ($("#newaccount .required").eq(i).val() == "")
        ready = false;
    }
    if (ready)
      $("#newaccount > #createaccount").button("enable");
  });
  
  $("#newaccount > #createaccount").button();
  $("#newaccount > #createaccount").click(function () {
    account = {}
    $("#newaccount input,select").each(function() {
      if ($(this).val() != "")
        account[$(this).attr("id")] = $(this).val();
    });
    $.ajax({
      type: "POST",
      url: apiurl,
      data: { "action": "editaccount", "account": JSON.stringify(account) },
      success: function(data) {
        if (data) {
          $("#newaccount").dialog("close");
          loadaccounts();
        } else {
          showerror("Could not add/edit account");
        }
      },
      error: function() {
        showerror("HTTP Error editing account");
      }
    });
  });

  $("#linktransactions div").droppable({
    drop: function (event, ui) {
        var t = parseInt($(ui.draggable).attr("id").substring(5));
        if ($(this).attr("id") == "parent") {
            linkparent = loadedtransactions[t]["id"];
            $(this).html("");
        } else {
            linkchildren.push(loadedtransactions[t]["id"])
        }
        $(this).append(loadedtransactions[t]["id"] + "<br>");
    },
    tolerance: "touch",
    hoverClass: "ui-state-active"
  });
  $("#linktransactions button").button();
  $("#linktransactions #clear").click(clearlink);
  $("#linktransactions #combine,#split,#dup").click(function () {
    $.ajax({
        type: "POST",
        url: apiurl,
        data: { "action": "link",
                "parent": linkparent,
                "children": JSON.stringify(linkchildren),
                "linktype": $(this).attr("id")
        },
        success: function(data) {
            if (data) {
                clearlink();
                loadtransactions();
            } else {
                showerror("Error linking transactions");
            }
        },
        error: function() {
            showerror("HTTP error linking transactions");
        }
    });
  });

  clearpage();
  
  $("body").addClass("ui-widget");

  $("th").addClass("ui-state-default");

});

jQuery.fn.center = function () {
    this.css("position","absolute");
    this.css("top", (($(window).height() - this.outerHeight()) / 2) +
                      $(window).scrollTop() + "px");
    this.css("left", (($(window).width() - this.outerWidth()) / 2) +
                       $(window).scrollLeft() + "px");
    return this;
}
