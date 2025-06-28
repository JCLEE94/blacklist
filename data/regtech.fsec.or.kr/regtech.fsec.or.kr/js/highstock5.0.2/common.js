/**
 * 날짜 : 2016.10.27
 * 이름 : 임정채
 * 설명 : highstock 이용한 차트(단일 차트)
 * 참조 : http://www.highcharts.com/
 *        - api              : http://api.highcharts.com/highstock
 *        - chart type       : http://api.highcharts.com/highcharts/plotOptions
 *        - theme            : http://www.highcharts.com/docs/chart-design-and-style/themes
 *        - theme collection : http://jkunst.com/highcharts-themes-collection/
 *        
 * chartType : 차트 타입(cloumn, line, bar, area, scatter, spline), pie는 데이터 구조가 달라 다르게 구현해야 함
 * cateList  : 제목 목록
 * dataList  : 데이터 목록
 * 
 * example   : var cateList = new Array("title1", "title2", "title3", "title4", "title5");      
 *             var dataList = new Array();   
 *             
 *             dataList.push({name:null,data:[]});                                        
 *             dataList.push({name:null,data:[]});
 *             dataList.push({name:null,data:[]});
 *             dataList.push({name:null,data:[]});
 *             dataList.push({name:null,data:[]});
 *             dataList.push({name:null,data:[]});
 *                                                                      
 *             dataList[0].name = "전사 전";                                
 *             dataList[0].data.push(5);
 *             
 *             dataList[1].name = "전사 중";                                
 *             dataList[1].data.push(5);  
 *             
 *             dataList[2].name = "전사 완료";                                
 *             dataList[2].data.push(5);
 *             
 *             dataList[3].name = "검증 중";                                
 *             dataList[3].data.push(5);
 *             
 *             dataList[4].name = "검증 완료";                                
 *             dataList[4].data.push(5);
 *             
 *             dataList[5].name = "검증 보류";                                
 *             dataList[5].data.push(5);
 ***********************************************************************************/
$.fn.singleChart = function(element, chartType, cateList, dataList) {

    // theme
    Highcharts.setOptions($.fn.theme_1());

    $(element).highcharts({
        chart: { // 차트 타입
            type: chartType
        },
        title: { // 차트 제목
            text: null
        },
        xAxis: { // 제목 기준
            min: 0,
            max: 0,
            categories: cateList
        },
        yAxis: { // 데이터 기준
            min: 0,
            allowDecimals: false,
            title: {
                text: null
            }
        },
        exporting: { // 내보내기
            buttons: {
                contextButton: {
                    x: 0,
                    y: 0
                }
            }
        },
        series: dataList // 데이터 목록
    });
};

/**
 * 날짜 : 2016.10.27
 * 이름 : 임정채
 * 설명 : highstock 이용한 차트(복수 차트)
 * 참조 : http://www.highcharts.com/
 *        - api              : http://api.highcharts.com/highstock
 *        - chart type       : http://api.highcharts.com/highcharts/plotOptions
 *        - theme            : http://www.highcharts.com/docs/chart-design-and-style/themes
 *        - theme collection : http://jkunst.com/highcharts-themes-collection/
 *        
 * chartType : 차트 타입(cloumn, line, bar, area, scatter, spline), pie는 데이터 구조가 달라 다르게 구현해야 함
 * cateList  : 제목 목록
 * dataList  : 데이터 목록
 * 
 * example   : var cateList = new Array("title1", "title2", "title3", "title4", "title5"); 
 *             var dataList = new Array();
 *                 dataList.push({name:null,data:[]});
 *                 dataList.push({name:null,data:[]});
 *                 dataList.push({name:null,data:[]});
 *                 dataList.push({name:null,data:[]});
 *                 dataList.push({name:null,data:[]});
 *                 dataList.push({name:null,data:[]});
 *                     
 *                 dataList[0].name = "전사전";
 *                 dataList[0].data.push(5);
 *                 dataList[0].data.push(3);
 *                 dataList[0].data.push(4);
 *                 dataList[0].data.push(7);
 *                 dataList[0].data.push(2);
 *                     
 *                 dataList[1].name = "전사중";
 *                 dataList[1].data.push(5);
 *                 dataList[1].data.push(3);
 *                 dataList[1].data.push(4);
 *                 dataList[1].data.push(7);
 *                 dataList[1].data.push(2);
 ***********************************************************************************/
$.fn.multiChart = function(element, chartType, cateList, dataList) {

    // theme
    Highcharts.setOptions($.fn.theme_1());

    $(element).highcharts({
        chart: { // 차트 타입
            type: chartType
        },
        title: { // 차트 제목
            text: null
        },
        xAxis: { // 제목 기준
            min: 0,
            max: (function() { // 5개 까지출력
                if (null == dataList) {
                    return 0;
                }
                return 4 < dataList[0].data.length ? 4 : dataList[0].data.length - 1;
            }()),
            scrollbar: {
                enabled: true
            },
            categories: cateList
        },
        yAxis: { // 데이터 기준
            min: 0,
            allowDecimals: false,
            title: {
                text: null
            }
        },
        exporting: { // 내보내기
            buttons: {
                contextButton: {
                    x: 0,
                    y: 0
                }
            }
        },
        series: dataList // 데이터 목록
    });
};

/**
 * 날짜 : 2016.10.27
 * 이름 : 임정채
 * 설명 : highstock 이용한 차트(복수 차트)
 * 참조 : http://www.highcharts.com/
 *        - api              : http://api.highcharts.com/highstock
 *        - chart type       : http://api.highcharts.com/highcharts/plotOptions
 *        - theme            : http://www.highcharts.com/docs/chart-design-and-style/themes
 *        - theme collection : http://jkunst.com/highcharts-themes-collection/
 *        
 * chartType : 차트 타입(cloumn, line, bar, area, scatter, spline), pie는 데이터 구조가 달라 다르게 구현해야 함
 * cateList  : 제목 목록
 * dataList  : 데이터 목록
 * 
 * example   : var cateList = new Array("title1", "title2", "title3", "title4", "title5"); 
 *             var dataList = new Array();
 *                 dataList.push({name:null,data:[]});
 *                 dataList.push({name:null,data:[]});
 *                 dataList.push({name:null,data:[]});
 *                 dataList.push({name:null,data:[]});
 *                 dataList.push({name:null,data:[]});
 *                 dataList.push({name:null,data:[]});
 *                     
 *                 dataList[0].name = "전사전";
 *                 dataList[0].data.push(5);
 *                 dataList[0].data.push(3);
 *                 dataList[0].data.push(4);
 *                 dataList[0].data.push(7);
 *                 dataList[0].data.push(2);
 *                     
 *                 dataList[1].name = "전사중";
 *                 dataList[1].data.push(5);
 *                 dataList[1].data.push(3);
 *                 dataList[1].data.push(4);
 *                 dataList[1].data.push(7);
 *                 dataList[1].data.push(2);
 ***********************************************************************************/
$.fn.multiChart2 = function(element, chartType, cateList, dataList) {
    // theme
    Highcharts.setOptions($.fn.theme_1());

    $(element).highcharts({
        chart: { // 차트 타입
            type: chartType
        },
        title: { // 차트 제목
            text: null
        },
        xAxis: { // 제목 기준
            min: 0,
            max: (function() { // 10개 까지출력
                if (null == dataList) {
                    return 0;
                }
                return 10 < dataList[0].data.length ? 10 : dataList[0].data.length - 1;
            }()),
            scrollbar: {
                enabled: true
            },
            categories: cateList
        },
        yAxis: { // 데이터 기준
            min: 0,
            allowDecimals: false,
            title: {
                text: null
            }
        },
        plotOptions: { // 데이터 표시
            bar: {
                dataLabels: {
                    enabled: true
                }
            }
        },
        exporting: { // 내보내기
            buttons: {
                contextButton: {
                    x: -25,
                    y: 0
                }
            }
        },
        series: dataList // 데이터 목록
    });
};

/**
 * 날짜 : 2016.10.27
 * 이름 : 임정채
 * 설명 : highstock 이용한 차트(복수 차트)
 * 참조 : http://www.highcharts.com/
 *        - api              : http://api.highcharts.com/highstock
 *        - chart type       : http://api.highcharts.com/highcharts/plotOptions
 *        - theme            : http://www.highcharts.com/docs/chart-design-and-style/themes
 *        - theme collection : http://jkunst.com/highcharts-themes-collection/
 *        
 * chartType : 차트 타입(cloumn, line, bar, area, scatter, spline), pie는 데이터 구조가 달라 다르게 구현해야 함
 * cateList  : 제목 목록
 * dataList  : 데이터 목록
 * 
 * example   : var cateList = new Array("title1", "title2", "title3", "title4", "title5"); 
 *             var dataList = new Array();
 *                 dataList.push({name:null,data:[]});
 *                 dataList.push({name:null,data:[]});
 *                 dataList.push({name:null,data:[]});
 *                 dataList.push({name:null,data:[]});
 *                 dataList.push({name:null,data:[]});
 *                 dataList.push({name:null,data:[]});
 *                     
 *                 dataList[0].name = "전사전";
 *                 dataList[0].data.push(5);
 *                 dataList[0].data.push(3);
 *                 dataList[0].data.push(4);
 *                 dataList[0].data.push(7);
 *                 dataList[0].data.push(2);
 *                     
 *                 dataList[1].name = "전사중";
 *                 dataList[1].data.push(5);
 *                 dataList[1].data.push(3);
 *                 dataList[1].data.push(4);
 *                 dataList[1].data.push(7);
 *                 dataList[1].data.push(2);
 ***********************************************************************************/
$.fn.multiChart2 = function(element, chartType, cateList, dataList) {
    // theme
    Highcharts.setOptions($.fn.theme_1());

    $(element).highcharts({
        chart: { // 차트 타입
            type: chartType
        },
        title: { // 차트 제목
            text: null
        },
        xAxis: { // 제목 기준
            min: 0,
            max: (function() { // 10개 까지출력
                if (null == dataList) {
                    return 0;
                }
                return 10 < dataList[0].data.length ? 10 : dataList[0].data.length - 1;
            }()),
            scrollbar: {
                enabled: true
            },
            categories: cateList
        },
        yAxis: { // 데이터 기준
            min: 0,
            allowDecimals: false,
            title: {
                text: null
            }
        },
        plotOptions: { // 데이터 표시
            bar: {
                dataLabels: {
                    enabled: true,
                    formatter: function() {
                        if (this.y === 0) {
                            return null;
                        } else {
                            return this.y;
                        }
                    }
                }
            }
        },
        exporting: { // 내보내기
            buttons: {
                contextButton: {
                    x: -25,
                    y: 0
                }
            }
        },
        series: dataList // 데이터 목록
    });
};
/**
 * 날짜 : 2016.11.02
 * 이름 : 임정채
 * 설명 : highstock 이용한 메인 차트(단일 차트)
 * 참조 : http://www.highcharts.com/
 *        - api              : http://api.highcharts.com/highstock
 *        - chart type       : http://api.highcharts.com/highcharts/plotOptions
 *        - theme            : http://www.highcharts.com/docs/chart-design-and-style/themes
 *        - theme collection : http://jkunst.com/highcharts-themes-collection/
 *        
 * chartType : 차트 타입(cloumn, line, bar, area, scatter, spline), pie는 데이터 구조가 달라 다르게 구현해야 함
 * cateList  : 제목 목록
 * dataList  : 데이터 목록
 * 
 * example   : var cateList = new Array("title1", "title2", "title3", "title4", "title5");      
 *             var dataList = new Array();   
 *             
 *             dataList.push({name:null,data:[]});                                        
 *             dataList.push({name:null,data:[]});
 *             dataList.push({name:null,data:[]});
 *             dataList.push({name:null,data:[]});
 *             dataList.push({name:null,data:[]});
 *             dataList.push({name:null,data:[]});
 *                                                                      
 *             dataList[0].name = "전사 전";                                
 *             dataList[0].data.push(5);
 *             
 *             dataList[1].name = "전사 중";                                
 *             dataList[1].data.push(5);  
 *             
 *             dataList[2].name = "전사 완료";                                
 *             dataList[2].data.push(5);
 *             
 *             dataList[3].name = "검증 중";                                
 *             dataList[3].data.push(5);
 *             
 *             dataList[4].name = "검증 완료";                                
 *             dataList[4].data.push(5);
 *             
 *             dataList[5].name = "검증 보류";                                
 *             dataList[5].data.push(5);
 ***********************************************************************************/
$.fn.mainSingleChart = function(element, title, chartType, cateList, dataList) {

    // theme
    Highcharts.setOptions($.fn.theme_1());

    $(element).highcharts({
        chart: { // 차트 타입
            type: chartType
        },
        title: { // 차트 제목
            text: title
        },
        xAxis: { // 제목 기준
            min: 0,
            max: 0,
            categories: cateList
        },
        yAxis: { // 데이터 기준
            min: 0,
            allowDecimals: false,
            title: {
                text: null
            }
        },
        exporting: { // 내보내기
            enabled: false,
            buttons: {
                contextButton: {
                    x: 0,
                    y: 0
                }
            }
        },
        series: dataList // 데이터 목록
    });
};

/**
 * 날짜 : 2016.11.02
 * 이름 : 임정채
 * 설명 : highstock 이용한 메인 차트(복수 차트)
 * 참조 : http://www.highcharts.com/
 *        - api              : http://api.highcharts.com/highstock
 *        - chart type       : http://api.highcharts.com/highcharts/plotOptions
 *        - theme            : http://www.highcharts.com/docs/chart-design-and-style/themes
 *        - theme collection : http://jkunst.com/highcharts-themes-collection/
 *        
 * chartType : 차트 타입(cloumn, line, bar, area, scatter, spline), pie는 데이터 구조가 달라 다르게 구현해야 함
 * cateList  : 제목 목록
 * dataList  : 데이터 목록
 * 
 * example   : var cateList = new Array("title1", "title2", "title3", "title4", "title5"); 
 *             var dataList = new Array();
 *                 dataList.push({name:null,data:[]});
 *                 dataList.push({name:null,data:[]});
 *                 dataList.push({name:null,data:[]});
 *                 dataList.push({name:null,data:[]});
 *                 dataList.push({name:null,data:[]});
 *                 dataList.push({name:null,data:[]});
 *                     
 *                 dataList[0].name = "전사전";
 *                 dataList[0].data.push(5);
 *                 dataList[0].data.push(3);
 *                 dataList[0].data.push(4);
 *                 dataList[0].data.push(7);
 *                 dataList[0].data.push(2);
 *                     
 *                 dataList[1].name = "전사중";
 *                 dataList[1].data.push(5);
 *                 dataList[1].data.push(3);
 *                 dataList[1].data.push(4);
 *                 dataList[1].data.push(7);
 *                 dataList[1].data.push(2);
 ***********************************************************************************/
$.fn.mainMultiChart = function(element, title, chartType, cateList, dataList) {

    // theme
    Highcharts.setOptions($.fn.theme_1());

    $(element).highcharts({
        chart: { // 차트 타입
            type: chartType
        },
        title: { // 차트 제목
            text: title
        },
        xAxis: { // 제목 기준
            min: 0,
            max: (function() { // 3개 까지출력
                if (null == dataList) {
                    return 0;
                }
                return 2 < dataList[0].data.length ? 2 : dataList[0].data.length - 1;
            }()),
            scrollbar: {
                enabled: false
            },
            categories: cateList
        },
        yAxis: { // 데이터 기준
            min: 0,
            allowDecimals: false,
            title: {
                text: null
            }
        },
        exporting: { // 내보내기
            enabled: false,
            buttons: {
                contextButton: {
                    x: 0,
                    y: 0
                }
            }
        },
        series: dataList // 데이터 목록
    });
};

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