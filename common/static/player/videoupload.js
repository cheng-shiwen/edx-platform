var swfobj = new SWFObject('uploader.swf', 'uploadswf', '80', '31', '8');
swfobj.addVariable("progress_interval", 1);
swfobj.addVariable("notify_url", "http://192.168.56.101:8081/notifystatus");
swfobj.addParam('allowFullscreen', 'true');
swfobj.addParam('allowScriptAccess', 'always');
swfobj.addParam('wmode', 'transparent');
swfobj.write('swfDiv');

var videosourceID = location.search.substr(1).split("=")[1];

function on_spark_selected_file(filename) {
	document.getElementById("videofile").value = filename;
}

function on_spark_upload_validated(status, videoid) {
	if (status == "OK") {
		// alert("上传正常, videoid: " + videoid);
		window.opener.document.getElementById(videosourceID).value = videoid;
	} else if (status == "NETWORK_ERROR") {
		alert("网络错误");
	} else {
		alert("API错误码：" + status);
	}
}

$(function() {
	$("#progressbar").progressbar({
		value: 0,
		change: function() {
			$(".progress-label").text("　" + $("#progressbar").progressbar("value") + "%");
			$(".ui-progressbar-value.ui-widget-header.ui-corner-left.ui-corner-right").css("background", "#66b93d");
		},
		complete: function() {
			$(".progress-label").text("上传完成！");
			$(".progress-label").css("color", "white");
		}
	});
});

function on_spark_upload_progress(progressNum) {
	if (progressNum == -1) {
		alert("上传出错：" + progressNum);
	} else {
		$("#progressbar").progressbar("value", progressNum);
	}
}

function submitvideo() {
	var title = "";
	var tag = encodeURIComponent(document.getElementById("tag").value, "utf-8");
	var description = encodeURIComponent(document.getElementById("description").value, "utf-8");
	var queryString = "title=" + title + "&tag=" + tag + "&description=" + description;
	$.ajax({
		type: "GET",
		async: false,
		url: '/checkpermission/' + queryString,
		success: function(data) {
			document.getElementById("uploadswf").start_upload(data['encrypt']);
	    }
	});
}

function uploadWinResize() {
	$('#T-videoupload').css('marginTop', ($(window).height() - 353) / 2 + 'px');
	$('#T-videoupload').css('marginLeft', ($(window).width() - 420) / 2 + 'px');
	$('#swfDiv').css('top', ($(window).height() - 353) / 2 + 79 + 'px');
	$('#swfDiv').css('left', ($(window).width() - 420) / 2 + 312 + 'px');
}
