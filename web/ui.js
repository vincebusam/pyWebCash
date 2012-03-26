apiurl = "api.py";
loadedtransactions = [];
showing = -1;
editedfields = []

function decoratedollar() {
  if ($(this).html().substring(0,1) == "$")
    return;
  amount = parseInt($(this).html());
  if (amount > 0)
    $(this).addClass("posnum");
  $(this).html("$"+Math.abs(amount/100).toFixed(2));
}

function loadaccounts() {
  $.ajax({
    type: "POST",
    url: apiurl,
    data: { "action": "accounts" },
    success: function(data) {
      for (i in data) {
        for (j in data[i]["subaccounts"]) {
          $("#accountstablebody").append("<tr><td>"+data[i]["name"]+"</td><td>"+data[i]["subaccounts"][j]["name"]+"</td><td class='dollar'>"+data[i]["subaccounts"][j]["amount"]+"</td><td>"+data[i]["subaccounts"][j]["date"]+"</td></tr>");
        }
      }
      $(".dollar").each(decoratedollar);
      $("#accounts").show();
    },
    error: function() {
      alert("Error loading accounts");
    }
  });
}

function showtransaction(t) {
  if (showing == t) {
    $("#transactiondetail").hide();
    showing = -1;
    return;
  }
  showing = t;
  editedfields = [];
  $("#transactiondetail > #file").hide();
  $("#transactiondetail > div").each(function () {
    name = $(this).attr("id");
    $("#transactiondetail > #"+name).html();
    if (loadedtransactions[t][name] != undefined)
      $("#transactiondetail > #"+name).html(loadedtransactions[t][name]);
  });
  //$("#transactiondetail > #desc").html(loadedtransactions[t]["desc"]);
  if (loadedtransactions[t]["file"] != undefined) {
    $("#transactiondetail > #file").attr("src",apiurl+"?image="+loadedtransactions[t]["id"]);
    $("#transactiondetail > #file").show();
  }
  $("#transactiondetail").show();
}

function loadtransactions() {
  $("#transtablebody").html("");
  $.ajax({
    type: "POST",
    url: apiurl,
    data: { "action": "search", "limit": 25, "query": '{"amount": "$ne:0" }' },
    success: function(data) {
      total = 0;
      loadedtransactions = data;
      for (t=0; t<data.length; t++) {
        $("#transtablebody").append("<tr class='transaction' id='trans"+t+"'><td class='date'>"+data[t]["date"]+"</td><td class='description'>"+data[t]["desc"]+"</td><td class='dollar'>"+data[t]["amount"]+"</td></tr>\n");
        total += data[t]["amount"];
      }
      $("#transactionsum").html(total);
      $(".dollar").each(decoratedollar);
      $(".transaction").click(function() {
        showtransaction(parseInt($(this).attr("id").substring(5)));
      });
      $("#transactions").show();
    },
    error: function() {
      alert("Transaction loading error");
    }
  });
}

$(document).ready(function () {
  $("#login").hide();
  $("#transactions").hide();
  $("#transactiondetail").hide();
  $("#accounts").hide();

  $('[contenteditable]').live('focus', function() {
    var $this = $(this);
    $this.data('before', $this.html());
      return $this;
  }).live('blur keyup paste', function() {
    var $this = $(this);
    if ($this.data('before') !== $this.html()) {
      $this.data('before', $this.html());
      if (editedfields.indexOf($(this).attr("id")) == -1)
        editedfields.push($(this).attr("id"));
    }
    return $this;
  });

  $.ajax({
    type: "POST",
    url: apiurl,
    data: { "action": "checklogin" },
    success: function(data) {
      if (data) {
        loadaccounts();
        loadtransactions();
      } else {
        $("#login").show();
      }
    },
    error: function() {
      $("#login").show();
    }
  });

  $("#loginsubmit").click(function () {
    $.ajax({
      type: "POST",
      url: apiurl,
      data: { "action": "login", "username": $("#username").val(), "password": $("#password").val() },
      success: function(data) {
        if (data) {
          $("#login").hide();
          loadaccounts();
          loadtransactions();
        } else {
          alert("Login Failed");
        }
      },
      error: function() {
        alert("Login Error");
      }
    });
  });

});
