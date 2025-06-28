/** 
 * 게시판에서 제목 클릭시 새창으로 열리는 구분값 번호
 */
var arrayUrlNo = ['1', '2', '6', '7', '9', '10'];

window.onbeforeunload = function(event) {
    if ((event.clientY < 0) || (event.altkey) || (event.clientY < 129) && (event.clientY > 107)) {
        $.ajax({
            url: "/logout"
        });
    }
}

////datepicker 날짜 형식
//$(function() {
//	$.datepicker.setDefaults({
//		dateFormat: 'yymmdd' //형식(20180629)
//	});
//});


//file폼 초기화
function initFileForm() {
    $(".files").each(function(i) {
        $(this).prop("name", $(this).prop("name").replace("files[]", "files[" + i + "]"));
    });

    $(".filesAdmin").each(function(i) {
        $(this).prop("name", $(this).prop("name").replace("filesAdmin[]", "filesAdmin[" + i + "]"));
    });

    $(".filesScenario").each(function(i) {
        $(this).prop("name", $(this).prop("name").replace("filesScenario[]", "filesScenario[" + i + "]"));
    });

    $(".filesEvidence").each(function(i) {
        $(this).prop("name", $(this).prop("name").replace("filesEvidence[]", "filesEvidence[" + i + "]"));
    });

    $(".auxiliaryFiles1").each(function(i) {
        $(this).prop("name", $(this).prop("name").replace("auxiliaryFiles1[]", "auxiliaryFiles1[" + i + "]"));
    });

    $(".auxiliaryFiles2").each(function(i) {
        $(this).prop("name", $(this).prop("name").replace("auxiliaryFiles2[]", "auxiliaryFiles2[" + i + "]"));
    });

    $(".auxiliaryFiles3").each(function(i) {
        $(this).prop("name", $(this).prop("name").replace("auxiliaryFiles3[]", "auxiliaryFiles3[" + i + "]"));
    });
}

function initFileForm2() {
    $(".files2").each(function(i) {
        $(this).prop("name", $(this).prop("name").replace("files2[]", "files2[" + i + "]"));
    });
}
/**
 * 날짜 : 2016.10.27
 * 이름 : 임정채
 * 설명 : highstock 테마 1
 * 참조 : http://www.highcharts.com/
 *        - api              : http://api.highcharts.com/highstock
 *        - chart type       : http://api.highcharts.com/highcharts/plotOptions
 *        - theme            : http://www.highcharts.com/docs/chart-design-and-style/themes
 *        - theme collection : http://jkunst.com/highcharts-themes-collection/
 ***********************************************************************************/
$.fn.theme_1 = function() {

    Highcharts.theme = {
        colors: ['#7cb5ec', '#f7a35c', '#90ee7e', '#7798BF', '#aaeeee', '#ff0066', '#eeaaee', '#55BF3B', '#DF5353', '#7798BF', '#aaeeee'],
        chart: {
            backgroundColor: null,
            style: {
                fontFamily: 'Dosis, sans-serif'
            }
        },
        title: {
            style: {
                fontSize: '12px',
                textTransform: 'uppercase'
            }
        },
        tooltip: {
            borderWidth: 0,
            backgroundColor: 'rgba(219,219,216,0.8)',
            shadow: false
        },
        legend: {
            itemStyle: {
                fontSize: '11px',
                fontWeight: 'nomal',
                fontFamily: 'Dosis, sans-serif'
            }
        },
        xAxis: {
            gridLineWidth: 1,
            labels: {
                style: {
                    fontSize: '12px'
                }
            }
        },
        yAxis: {
            minorTickInterval: 'auto',
            title: {
                style: {
                    textTransform: 'uppercase'
                }
            },
            labels: {
                style: {
                    fontSize: '12px'
                }
            }
        },
        plotOptions: {
            candlestick: {
                lineColor: '#404048'
            }
        },

        // General
        background2: '#F0F0EA'
    };

    return Highcharts.theme;
}

/**
 * 날짜 : 2016.10.27
 * 이름 : 임정채
 * 설명 : highstock 테마 2
 * 참조 : http://www.highcharts.com/
 *        - api              : http://api.highcharts.com/highstock
 *        - chart type       : http://api.highcharts.com/highcharts/plotOptions
 *        - theme            : http://www.highcharts.com/docs/chart-design-and-style/themes
 *        - theme collection : http://jkunst.com/highcharts-themes-collection/
 ***********************************************************************************/
$.fn.theme_2 = function() {

    Highcharts.theme = {
        colors: ['#f45b5b', '#8085e9', '#8d4654', '#7798BF', '#aaeeee', '#ff0066', '#eeaaee',
            '#55BF3B', '#DF5353', '#7798BF', '#aaeeee'
        ],
        chart: {
            backgroundColor: null,
            style: {
                fontFamily: 'Signika, serif'
            }
        },
        title: {
            style: {
                color: 'black',
                fontSize: '16px',
                fontWeight: 'bold'
            }
        },
        subtitle: {
            style: {
                color: 'black'
            }
        },
        tooltip: {
            borderWidth: 0
        },
        legend: {
            itemStyle: {
                fontWeight: 'bold',
                fontSize: '13px'
            }
        },
        xAxis: {
            labels: {
                style: {
                    color: '#6e6e70'
                }
            }
        },
        yAxis: {
            labels: {
                style: {
                    color: '#6e6e70'
                }
            }
        },
        plotOptions: {
            series: {
                shadow: true
            },
            candlestick: {
                lineColor: '#404048'
            },
            map: {
                shadow: false
            }
        },

        // Highstock specific
        navigator: {
            xAxis: {
                gridLineColor: '#D0D0D8'
            }
        },
        rangeSelector: {
            buttonTheme: {
                fill: 'white',
                stroke: '#C0C0C8',
                'stroke-width': 1,
                states: {
                    select: {
                        fill: '#D0D0D8'
                    }
                }
            }
        },
        scrollbar: {
            trackBorderColor: '#C0C0C8'
        },

        // General
        background2: '#E0E0E8'

    };

    return Highcharts.theme;
}

/**
 * 날짜 : 2016.10.27
 * 이름 : 임정채
 * 설명 : highstock 테마 3
 * 참조 : http://www.highcharts.com/
 *        - api              : http://api.highcharts.com/highstock
 *        - chart type       : http://api.highcharts.com/highcharts/plotOptions
 *        - theme            : http://www.highcharts.com/docs/chart-design-and-style/themes
 *        - theme collection : http://jkunst.com/highcharts-themes-collection/
 ***********************************************************************************/
$.fn.theme_3 = function() {

    Highcharts.theme = {
        colors: ['#2b908f', '#90ee7e', '#f45b5b', '#7798BF', '#aaeeee', '#ff0066', '#eeaaee',
            '#55BF3B', '#DF5353', '#7798BF', '#aaeeee'
        ],
        chart: {
            backgroundColor: {
                linearGradient: {
                    x1: 0,
                    y1: 0,
                    x2: 1,
                    y2: 1
                },
                stops: [
                    [0, '#2a2a2b'],
                    [1, '#3e3e40']
                ]
            },
            style: {
                fontFamily: '\'Unica One\', sans-serif'
            },
            plotBorderColor: '#606063'
        },
        title: {
            style: {
                color: '#E0E0E3',
                textTransform: 'uppercase',
                fontSize: '20px'
            }
        },
        subtitle: {
            style: {
                color: '#E0E0E3',
                textTransform: 'uppercase'
            }
        },
        xAxis: {
            gridLineColor: '#707073',
            labels: {
                style: {
                    color: '#E0E0E3'
                }
            },
            lineColor: '#707073',
            minorGridLineColor: '#505053',
            tickColor: '#707073',
            title: {
                style: {
                    color: '#A0A0A3'

                }
            }
        },
        yAxis: {
            gridLineColor: '#707073',
            labels: {
                style: {
                    color: '#E0E0E3'
                }
            },
            lineColor: '#707073',
            minorGridLineColor: '#505053',
            tickColor: '#707073',
            tickWidth: 1,
            title: {
                style: {
                    color: '#A0A0A3'
                }
            }
        },
        tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.85)',
            style: {
                color: '#F0F0F0'
            }
        },
        plotOptions: {
            series: {
                dataLabels: {
                    color: '#B0B0B3'
                },
                marker: {
                    lineColor: '#333'
                }
            },
            boxplot: {
                fillColor: '#505053'
            },
            candlestick: {
                lineColor: 'white'
            },
            errorbar: {
                color: 'white'
            }
        },
        legend: {
            itemStyle: {
                color: '#E0E0E3'
            },
            itemHoverStyle: {
                color: '#FFF'
            },
            itemHiddenStyle: {
                color: '#606063'
            }
        },
        credits: {
            style: {
                color: '#666'
            }
        },
        labels: {
            style: {
                color: '#707073'
            }
        },

        drilldown: {
            activeAxisLabelStyle: {
                color: '#F0F0F3'
            },
            activeDataLabelStyle: {
                color: '#F0F0F3'
            }
        },

        navigation: {
            buttonOptions: {
                symbolStroke: '#DDDDDD',
                theme: {
                    fill: '#505053'
                }
            }
        },

        // scroll charts
        rangeSelector: {
            buttonTheme: {
                fill: '#505053',
                stroke: '#000000',
                style: {
                    color: '#CCC'
                },
                states: {
                    hover: {
                        fill: '#707073',
                        stroke: '#000000',
                        style: {
                            color: 'white'
                        }
                    },
                    select: {
                        fill: '#000003',
                        stroke: '#000000',
                        style: {
                            color: 'white'
                        }
                    }
                }
            },
            inputBoxBorderColor: '#505053',
            inputStyle: {
                backgroundColor: '#333',
                color: 'silver'
            },
            labelStyle: {
                color: 'silver'
            }
        },

        navigator: {
            handles: {
                backgroundColor: '#666',
                borderColor: '#AAA'
            },
            outlineColor: '#CCC',
            maskFill: 'rgba(255,255,255,0.1)',
            series: {
                color: '#7798BF',
                lineColor: '#A6C7ED'
            },
            xAxis: {
                gridLineColor: '#505053'
            }
        },

        scrollbar: {
            barBackgroundColor: '#808083',
            barBorderColor: '#808083',
            buttonArrowColor: '#CCC',
            buttonBackgroundColor: '#606063',
            buttonBorderColor: '#606063',
            rifleColor: '#FFF',
            trackBackgroundColor: '#404043',
            trackBorderColor: '#404043'
        },

        // special colors for some of the
        legendBackgroundColor: 'rgba(0, 0, 0, 0.5)',
        background2: '#505053',
        dataLabelsColor: '#B0B0B3',
        textColor: '#C0C0C0',
        contrastTextColor: '#F0F0F3',
        maskColor: 'rgba(255,255,255,0.3)'
    };

    return Highcharts.theme;
}

//파일 다운로드
function fnCmdFileDownload(fileNo, makeName, form) {
    $("#fileNo").val(fileNo);
    $("#makeName").val(makeName);
    $("#" + form).attr("action", "/common/file/downloadFile").submit();
}


//제출 기관 그룹 편집과 관련된 함수
var group = {
    //제출 기관 그룹 정보를 가져온다.
    fnOpenEditOrgan: function() {

        $.ajax({
            async: true,
            type: 'get',
            url: "/report/apply/groupListJson",
            dataType: "json",
            data: null,
            success: function(data) {

                group.fnGroupEditHtml(data);
                common.modalPopShow('#orgGroupMdy', '500px');
            }
        });
    },



    //제출기관 그룹 편집 그리기
    fnGroupEditHtml: function(list) {
        var vHtml = "";
        if (list.length > 0) {

            for (var i = 0; i < list.length; i++) {
                var group = list[i];

                vHtml += '<li>';
                vHtml += '	<div class="group">';
                vHtml += '		<span class="mdy_input">';

                vHtml += '			<input type="text" value="' + group.organGroupName + ' (' + group.organGroupCnt + ')" title="제출기관 그룹명" disabled>';
                vHtml += '			<span style="display:none;">' + group.organGroupName + '</span>';
                vHtml += '		</span>';
                vHtml += '		<span class="buttons">';
                vHtml += '			<button class="btn_mdy" type="button" onclick="group.fnShowEditGroupItem(this)">편집</button>';
                vHtml += '			<button class="btn_garbage" type="button" onclick="group.fnDeleteGroup(' + group.organGroupCode + ')">삭제</button>';
                vHtml += '			<button class="btnIn type1 btn_save" type="button" onclick="group.fnEditGroupName(' + group.organGroupCode + ', this)">저장</button>';
                vHtml += '		</span>';
                vHtml += '		<a  class="btn_open" href="#none">기관명 보기</a>';
                vHtml += '	</div>';
                if (group.organs.length > 0) {
                    vHtml += '	<div class="group_in">';
                    vHtml += '		<ul class="inner_list">';

                    for (var j = 0; j < group.organs.length; j++) {
                        var organ = group.organs[j];
                        vHtml += '<li>' + organ.organName + ' <button class="btn_garbage" type="button" onclick="group.fnDeleteOrgan(' + organ.organBelow.organBelowNo + ')">삭제</button></li>';
                    }
                    vHtml += '	</ul>';
                }
                vHtml += '</div>';
                vHtml += '</li>';
            }

        }
        $("#ulGroupArea").html(vHtml);
        sub.orgList();
    },

    fnShowEditGroupItem: function(obj) {
        var txt = $(obj).parent().parent().find(".mdy_input").find("span").html();

        $(obj).parent().parent().find("input[type='text']").val(unescapeEditor(txt));
    },


    //그룹명을 수정한다.
    fnEditGroupName: function(organGroupNo, obj) {

        var txt = $(obj).parent().parent().find("input[type='text']").val();

        var params = {
            "organGroupNo": organGroupNo,
            "name": txt
        };
        $.ajax({
            type: 'post',
            url: "/report/apply/editGroupNameJson",
            dataType: "json",
            data: params,
            success: function(data) {
                alert("그룹명을 변경했습니다.");
                group.fnGroupEditHtml(data);
                //	 			$(obj).closest('.group').removeClass('on')
                //	 			$(obj).closest('.group').find('.mdy_input input').prop('disabled',true);
            }
        });
    },

    //그룹을 삭제한다.
    fnDeleteGroup: function(organGroupNo) {

        if (confirm("그룹을 삭제하시겠습니까?")) {
            $.ajax({
                type: 'post',
                url: "/report/apply/deleteGroupJson",
                dataType: "json",
                data: {
                    "organGroupNo": organGroupNo
                },
                success: function(data) {
                    alert("그룹을 삭제했습니다.");
                    group.fnGroupEditHtml(data);
                }
            });
        }
    },


    //그룹에 속한 기관 정보를 삭제한다.
    fnDeleteOrgan: function(organBelowNo) {
        if (confirm("해당 기관을 그룹에서 제외하시겠습니까?")) {
            $.ajax({
                type: 'post',
                url: "/report/apply/deleteOrganJson",
                dataType: "json",
                data: {
                    "organBelowNo": organBelowNo
                },
                success: function(data) {
                    alert("해당 기관을 그룹에서 삭제했습니다.");
                    group.fnGroupEditHtml(data);
                }
            });
        }
    }
}

//새창여는 스크립트
function WinOpen(Url, OpenName, Wid, Hei, scrollFlag) { //새창여는 스크립트
    var scroll;
    if (scrollFlag == "Y") {
        scroll = "yes";
    } else {
        scroll = "no";
    }
    var ScreenWidth = screen.width; //스크린사이즈(가로)
    var ScreenHeight = screen.height; //스크린사이즈(세로)
    var OpenWinWidth = Wid; //오픈할 창 사이즈(가로)
    var OpenWinHeight = Hei; //오픈할 창 사이즈(세로)
    var OpenLeft = (ScreenWidth - OpenWinWidth) / 2; //정확하게 가운데(가로) 열기 위해 계산한다
    var OpenTop = (ScreenHeight - OpenWinHeight) / 2; //정확하게 가운데(세로) 열기 위해 계산한다
    var OpenWinStatus = "left=" + OpenLeft + ",top=" + OpenTop + ",toolbar=no,location=no,directories=no,status=no,menubar=no,scrollbars=" + scroll + ",resizable=no,copyhistory=yes,width=" + OpenWinWidth + ",height=" + OpenWinHeight + "";

    window.open(Url, OpenName, OpenWinStatus);
    return;
}

//검색영역 인풋 초기화
function fnCmdCommonReset() {
    $(':input', '.filter_wrap').not(':button, :submit, :reset, :hidden')
        .val('');
}

//레이어 닫기
function fnCmdLayerCancle(layerName) {
    common.modalPopHide(layerName);
}

// 레이어팝업 닫기
$('.layerPopupClose').click(function() {
    common.modalPopHide($(this));
})

//두자리 만들기(한자리인 경우 앞에 0을 붙인다)
function leadingZeros(n, digits) {
    var zero = '';
    n = n.toString();

    if (n.length < digits) {
        for (var i = 0; i < digits - n.length; i++)
            zero += '0';
    }
    return zero + n;
}

//입력값 숫자만 입력
function onlyNumber(obj) {
    regexp = /[^0-9]/gi;    
    v = $(obj).val();    
    if (regexp.test(v)) {       
        alert("숫자만 입력가능 합니다.");       
        $(obj).val(v.replace(regexp, ''));    
    }
}

//입력값 숫자만 입력
function onlyNumber2(obj) {
    regexp = /[^0-9.]/gi;    
    v = $(obj).val();    
    if (regexp.test(v)) {       
        alert("숫자 '.'만 입력가능 합니다.");       
        $(obj).val(v.replace(regexp, ''));    
    }
}

//  "/" 허용 포함 (IP 대역입력)
function onlyNumber3(obj) {
    regexp = /[^0-9./]/gi;    
    v = $(obj).val();    
    if (regexp.test(v)) {       
        alert("숫자 '.' 또는 '/' 만 입력가능 합니다.");       
        $(obj).val(v.replace(regexp, ''));    
    }
}

function fnChkByte(obj, maxByte) {
    var str = obj.value;
    var str_len = str.length;

    var rbyte = 0;
    var rlen = 0;
    var one_char = "";
    var str2 = "";

    for (var i = 0; i < str_len; i++) {
        one_char = str.charAt(i);
        if (escape(one_char).length > 4) {
            rbyte += 3; //한글2Byte
        } else {
            rbyte++; //영문 등 나머지 1Byte
        }

        if (rbyte <= maxByte) {
            rlen = i + 1; //return할 문자열 갯수
        }
    }

    if (rbyte > maxByte) {
        alert("한글 666자 / 영문 " + maxByte + "자를 초과 입력할 수 없습니다.");
        str2 = str.substr(0, rlen); //문자열 자르기
        obj.value = str2;
        fnChkByte(obj, maxByte);
    } else {
        //document.getElementById('byteInfo').innerText = rbyte;
    }
}


//jquery calendar 기본 옵션
function fnCommonCalendar(id, defaultDate, otherOptions) {
    var defaultOptions = {

        header: {
            left: '',
            center: 'prev title next',
            right: ''
        },
        locale: 'ko',
        defaultDate: defaultDate,
        navLinks: false, // can click day/week names to navigate views
        editable: false,
        allDayDefault: false,
        defaultView: "month",
        eventLimit: true,
        views: {

        },
        //			eventMouseover: function( eventObj, jsEvent, view ) {
        //				$el.popover({
        //					title : eventObj.title,
        //					content : eventObj.description,
        //					trigger : 'hover',
        //					placement : 'top',
        //					container : 'body'
        //				});
        //			},
        eventClick: function(calEvent, jsEvent, view) {
            //alert('Event: ' + calEvent.title + "항목 클릭");
        }
    };
    if (otherOptions) {
        defaultOptions = $.extend({}, defaultOptions, otherOptions);
    }
    var calendar = $('#' + id).fullCalendar(defaultOptions);

}

function unescapeEditor(strTemp) {
    strTemp = strTemp.replace(/&lt;/g, "<");
    strTemp = strTemp.replace(/&gt;/g, ">");
    strTemp = strTemp.replace(/&amp;/g, "&");
    strTemp = strTemp.replace(/&quot;/g, "\"");
    strTemp = strTemp.replace(/&apos;/g, "\'");
    return strTemp;
}

function escapeEditor(strTemp) {
    strTemp = strTemp.replace(/</g, "&lt;");
    strTemp = strTemp.replace(/>/g, "&gt;");
    strTemp = strTemp.replace(/&/g, "&amp;");
    strTemp = strTemp.replace(/\"/g, "&quot;");
    strTemp = strTemp.replace(/\'/g, "&apos;");
    return strTemp;
}

function textAreaBr(val) {
    val.replace(/(?:\r\n|\r|\n)/g, "<br />");
    return val;
}

var oEditors = [];

function initEditor(id) {
    nhn.husky.EZCreator.createInIFrame({
        oAppRef: oEditors,
        elPlaceHolder: id,
        sSkinURI: "/js/smartEditor/SmartEditor2Skin.html",
        htParams: {
            bUseToolbar: true, // 툴바 사용 여부 (true:사용/ false:사용하지 않음)
            bUseVerticalResizer: true, // 입력창 크기 조절바 사용 여부 (true:사용/ false:사용하지 않음)
            bUseModeChanger: false, // 모드 탭(Editor | HTML | TEXT) 사용 여부 (true:사용/ false:사용하지 않음)
            //aAdditionalFontList : aAdditionalFontSet,     // 추가 글꼴 목록
            fOnBeforeUnload: function() {

            }
        }, //boolean
        fOnAppLoad: function() {

        },
        fCreator: "createSEditor2"
    });
}

//새창여는 스크립트
function WinOpen(Url, OpenName, Wid, Hei, scrollFlag) { //새창여는 스크립트
    var scroll;
    if (scrollFlag == "Y") {
        scroll = "yes";
    } else {
        scroll = "no";
    }
    var ScreenWidth = screen.width; //스크린사이즈(가로)
    var ScreenHeight = screen.height; //스크린사이즈(세로)
    var OpenWinWidth = Wid; //오픈할 창 사이즈(가로)
    var OpenWinHeight = Hei; //오픈할 창 사이즈(세로)
    var OpenLeft = (ScreenWidth - OpenWinWidth) / 2; //정확하게 가운데(가로) 열기 위해 계산한다
    var OpenTop = (ScreenHeight - OpenWinHeight) / 2; //정확하게 가운데(세로) 열기 위해 계산한다
    var OpenWinStatus = "left=0,top=0,toolbar=no,location=no,directories=no,status=no,menubar=no,scrollbars=" + scroll + ",resizable=no,copyhistory=yes,width=" + OpenWinWidth + ",height=" + OpenWinHeight + "";

    window.open(Url, OpenName, OpenWinStatus);
    return;
}