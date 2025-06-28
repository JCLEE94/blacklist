'use strict';

var common = {

    gnb: function() {

        var $gnb = $('#gnb'),
            $depth2 = $gnb.find('.depth2'),
            $m_depth1 = $gnb.find('.depth1 li'),
            $m_depth2 = $gnb.find('.depth2 li'),
            $depth3 = $gnb.find('.depth3'),
            delay = 100,
            setTime;


        /** 기존 코드
        $gnb.mouseenter(function(){
        	if(!$('.btn_search').hasClass('on')){ gnb_open(); }
        	$m_depth2.off('click').on('click',function(e){
        		e.stopPropagation();
        		$depth2.css('height','auto');
        		if($(this).hasClass('in')){
        			e.preventDefault();
        			if(!$(this).hasClass('open')){
        				$m_depth2.removeClass('open');
        				$(this).addClass('open');
        				$depth3.removeClass('active');
        				$(this).find('.depth3').addClass('active');
        			}else{
        				$(this).removeClass('open');
        				$(this).find('.depth3').removeClass('active');
        			}
        		}
        	})
        	$m_depth2.mouseleave(function(e){ e.stopPropagation(); })

        }).mouseleave(function(){ gnb_close(); })
		
        $('#contents').mouseenter(function(e){ gnb_close(); })
        **/
        /***************************************************************/
        $gnb.on('mouseenter focusin', function() {
            if (!$('.btn_search').hasClass('on')) {
                document.onkeydown = keydown;

                function keydown(evt) {
                    if (!evt) evt = event;
                    if ($('#btn_search').is(':focus') && evt.shiftKey && evt.keyCode === 9) {
                        setTimeout(function() {
                            $gnb.find('.depth2 > li > a').last().focus()
                        }, 1);
                    }
                }
                gnb_open();
            }
            $m_depth2.off('click').on('click', function(e) {
                e.stopPropagation();
                $depth2.css('height', 'auto');
                if ($(this).hasClass('in')) {
                    e.preventDefault();
                    if (!$(this).hasClass('open')) {
                        $m_depth2.removeClass('open');
                        $(this).addClass('open');
                        $depth3.removeClass('active');
                        $(this).find('.depth3').addClass('active');
                    } else {
                        $(this).removeClass('open');
                        $(this).find('.depth3').removeClass('active');
                    }
                }
            })
            $m_depth2.on('mouseleave focusout', function(e) {
                e.stopPropagation();
            })

        }).on('mouseleave focusout', function() {
            gnb_close();
        })

        $('#contents').on('mouseenter focusin', function(e) {
            gnb_close();
        })
        /******************************************************** 변경 코드 **/

        function gnb_open() {
            $depth2.stop().slideDown(150, function() {
                $depth2.css('height', 'auto')
            })
            $gnb.css('border-bottom', '1px solid #ccc');
        }

        function gnb_close() {
            $depth2.stop().slideUp(100, function() {
                $depth2.css('height', 'auto')
            });
            $gnb.css('border-bottom', 'none');
            $m_depth1.children('a').removeClass('on');
            $m_depth2.removeClass('open');
            $depth3.removeClass('active');
        }
    },

    top_menu: function() {
        var menu = $('.top_menu').find('li > a');
        menu.on({
            mouseenter: function() {
                var txt = $(this).find('.txt'),
                    left = parseInt(($(this).find('.txt').outerWidth() + 4) / 2);

                txt.css({
                    'margin-left': '-' + left + 'px',
                    'opacity': '1',
                    'z-index': '10'
                })
            },
            mouseleave: function() {
                var txt = $(this).find('.txt');
                txt.css({
                    'opacity': '',
                    'z-index': ''
                })
            }
        });
    },

    tabmenu: function(target) {
        var $tabBox = $(target).find('.tab_wrap'),
            $tabmenu = $tabBox.find('.tab_menu li'),
            $tabCont = $tabBox.find('.tab_content');

        $tabBox.each(function() {
            //if(!$(this).hasClass('no_tab')){$(this).find($tabmenu).eq(0).addClass('active');}
            $(this).find($tabCont).eq(0).css('display', 'block');
        })
        $tabmenu.click(function() {
            var idx = $(this).index();
            $tabmenu.removeClass('active');
            $(this).addClass('active');

            if (!$(this).closest('.tab_wrap').hasClass('no_tab')) {
                $(this).parent().siblings($tabCont).css('display', 'none');
                $(this).closest('.tab_wrap').find('.tab_content').eq(idx).css('display', 'block');
            }

            if ($(this).closest($tabBox).hasClass('type1')) {
                $tabmenu.css('border-right', '');
                $(this).prev().css('border-right', 'none');
            }
        })

    },

    selectmenu: function() {
        $('.selectbox select').selectmenu({
            open: function() {
                if ($(this).closest('.layer_box')) {

                    $(this).selectmenu("menuWidget").parent('.ui-selectmenu-open').css('z-index', 1000);
                }
                if ($(this).closest('.selectbox').hasClass('type2')) {
                    $(this).selectmenu("menuWidget").parent('.ui-selectmenu-open').addClass('high');
                }

            },
            change: function(event, ui) {
                if ($(this).closest('.selectbox').hasClass('type1')) {
                    $(this).closest('.selectbox').addClass('on');
                }
                $(this).val(ui.item.value).change();

            }

        });


    },

    calendar: function() {
        $('.calendar').filter(function() {
            var btn = $('.calendar input');
            btn.datepicker({
                showOn: "both",
                buttonImage: "/images/btn_calendar.png",
                dateFormat: 'yymmdd',
                prevText: '이전 달',
                nextText: '다음 달',
                monthNames: ['1월', '2월', '3월', '4월', '5월', '6월', '7월', '8월', '9월', '10월', '11월', '12월'],
                monthNamesShort: ['1월', '2월', '3월', '4월', '5월', '6월', '7월', '8월', '9월', '10월', '11월', '12월'],
                dayNames: ['일', '월', '화', '수', '목', '금', '토'],
                dayNamesShort: ['일', '월', '화', '수', '목', '금', '토'],
                dayNamesMin: ['일', '월', '화', '수', '목', '금', '토'],
                showMonthAfterYear: true,
                changeMonth: true,
                changeYear: true,
                yearSuffix: '년',
                yearRange: "c-50:c+10"
            })
            //$(this).prev('input').focus();
        });

    },

    list_sorting: function() {
        $('.tbl').filter(function() {

            // 페이지 로딩시 값 확인
            var sortVale = $("#findSort").val();
            //console.log("Sort : "+sortVale);
            if (sortVale != "") {

                $('.sort').each(function(idx, el) {
                    if ($(el).val() == sortVale) {
                        $(el).addClass('active');
                    }
                });
            }

            $('.sort').click(function() {

                // 전체 초기화
                $('.sort').removeClass('active');
                $("#findSort").val("");

                // 선택 당시 상태 값
                $(this).addClass('active');
                $("#findSort").val($(this).val());
                fnSearch();
            })
        })
    },

    accordian: function() {
        $('.acc_wrap').filter(function() {
            var wrap = $(this);
            var win_hei = $(window).outerHeight();

            if (wrap.hasClass('eval_items')) {
                wrap.children('ol').children('li').eq(0).find('.acc_btn').addClass('active');
                wrap.children('ol').children('li').eq(0).find('.acc_cont').css('display', 'block');
            }

            $(this).find('.btn_view').click(function() {
                var btn = $(this).parent('.acc_btn');
                var st = $(window).scrollTop();

                if (!btn.hasClass('active')) {
                    //init();
                    btn.addClass('active');

                    if (btn.parent('.top_btns').length > 0) {
                        btn.parent().next('.acc_cont').css('display', 'block');
                    } else {
                        btn.next('.acc_cont').css('display', 'block');
                    }

                } else {
                    btn.removeClass('active');
                    if (btn.parent('.top_btns').length > 0) {

                        btn.parent().next('.acc_cont').css('display', 'none');
                    } else {
                        btn.next('.acc_cont').css('display', 'none');
                    }

                }
                //내용이 긴경우 클릭버튼 상단이동 방지
                var top = ($(this).offset().top) - 180
                if (st > win_hei) {
                    $(window).scrollTop(top)
                }

                sub.hiddenCont();

            });


            if (wrap.find('.btn_view').length == 0 && wrap.find('.btn_view_info').length == 0) {
                $('.acc_btn').click(function() {
                    var btn = $(this);
                    if (!btn.hasClass('active')) {
                        //init();
                        btn.addClass('active');

                        if (btn.parent('.top_btns').length > 0) {
                            btn.parent().next('.acc_cont').css('display', 'block');
                        } else {
                            btn.next('.acc_cont').css('display', 'block');
                        }

                    } else {
                        btn.removeClass('active');
                        if (btn.parent('.top_btns').length > 0) {

                            btn.parent().next('.acc_cont').css('display', 'none');
                        } else {
                            btn.next('.acc_cont').css('display', 'none');
                        }

                    }
                });
            }

            if (wrap.hasClass('eval_items_new')) {
                wrap.children('ol').children('li').children('span').children('span').eq(0).find('.acc_btn').addClass('active');
                wrap.children('ol').children('li').eq(0).find('.info_cont1').css('display', 'block');
            }

            $(this).find('.btn_view_info').click(function() {
                var btn = $(this).parent('.acc_btn');
                var st = $(window).scrollTop();

                if (!btn.hasClass('active')) {
                    $(".ctit").each(function() {
                        $(this).removeClass("active");
                    });

                    btn.addClass('active');

                    if ($(this).hasClass('cont1')) {
                        wrap.children('ol').children('li').eq(0).find('.info_cont1').css('display', 'block');
                        wrap.children('ol').children('li').eq(0).find('.info_cont2').css('display', 'none');
                        wrap.children('ol').children('li').eq(0).find('.info_cont3').css('display', 'none');
                        wrap.children('ol').children('li').eq(0).find('.info_cont4').css('display', 'none');
                        wrap.children('ol').children('li').eq(0).find('.info_cont5').css('display', 'none');
                    } else if ($(this).hasClass('cont2')) {
                        wrap.children('ol').children('li').eq(0).find('.info_cont1').css('display', 'none');
                        wrap.children('ol').children('li').eq(0).find('.info_cont2').css('display', 'block');
                        wrap.children('ol').children('li').eq(0).find('.info_cont3').css('display', 'none');
                        wrap.children('ol').children('li').eq(0).find('.info_cont4').css('display', 'none');
                        wrap.children('ol').children('li').eq(0).find('.info_cont5').css('display', 'none');
                    } else if ($(this).hasClass('cont3')) {
                        wrap.children('ol').children('li').eq(0).find('.info_cont1').css('display', 'none');
                        wrap.children('ol').children('li').eq(0).find('.info_cont2').css('display', 'none');
                        wrap.children('ol').children('li').eq(0).find('.info_cont3').css('display', 'block');
                        wrap.children('ol').children('li').eq(0).find('.info_cont4').css('display', 'none');
                        wrap.children('ol').children('li').eq(0).find('.info_cont5').css('display', 'none');
                    } else if ($(this).hasClass('cont4')) {
                        wrap.children('ol').children('li').eq(0).find('.info_cont1').css('display', 'none');
                        wrap.children('ol').children('li').eq(0).find('.info_cont2').css('display', 'none');
                        wrap.children('ol').children('li').eq(0).find('.info_cont3').css('display', 'none');
                        wrap.children('ol').children('li').eq(0).find('.info_cont4').css('display', 'block');
                        wrap.children('ol').children('li').eq(0).find('.info_cont5').css('display', 'none');
                    } else if ($(this).hasClass('cont5')) {
                        wrap.children('ol').children('li').eq(0).find('.info_cont1').css('display', 'none');
                        wrap.children('ol').children('li').eq(0).find('.info_cont2').css('display', 'none');
                        wrap.children('ol').children('li').eq(0).find('.info_cont3').css('display', 'none');
                        wrap.children('ol').children('li').eq(0).find('.info_cont4').css('display', 'none');
                        wrap.children('ol').children('li').eq(0).find('.info_cont5').css('display', 'block');
                    }

                }

                //내용이 긴경우 클릭버튼 상단이동 방지
                var top = ($(this).offset().top) - 180
                if (st > win_hei) {
                    $(window).scrollTop(top)
                }

                sub.hiddenCont();

            });

            $(this).find('.sub_tab_btn').click(function() {
                var st = $(window).scrollTop();
                var chk_id = $(this).attr('id');

                if (chk_id == "k_t1") {
                    $('.info_cont1').css('display', 'block');
                    $('.info_cont2').css('display', 'none');
                    $('.info_cont3').css('display', 'none');
                    $('.info_cont4').css('display', 'none');
                    $('.info_cont5').css('display', 'none');
                } else if (chk_id == "k_t2") {
                    $('.info_cont1').css('display', 'none');
                    $('.info_cont2').css('display', 'block');
                    $('.info_cont3').css('display', 'none');
                    $('.info_cont4').css('display', 'none');
                    $('.info_cont5').css('display', 'none');
                } else if (chk_id == "k_t3") {
                    $('.info_cont1').css('display', 'none');
                    $('.info_cont2').css('display', 'none');
                    $('.info_cont3').css('display', 'block');
                    $('.info_cont4').css('display', 'none');
                    $('.info_cont5').css('display', 'none');
                } else if (chk_id == "k_t4") {
                    $('.info_cont1').css('display', 'none');
                    $('.info_cont2').css('display', 'none');
                    $('.info_cont3').css('display', 'none');
                    $('.info_cont4').css('display', 'block');
                    $('.info_cont5').css('display', 'none');
                } else if (chk_id == "k_t5") {
                    $('.info_cont1').css('display', 'none');
                    $('.info_cont2').css('display', 'none');
                    $('.info_cont3').css('display', 'none');
                    $('.info_cont4').css('display', 'none');
                    $('.info_cont5').css('display', 'block');
                }

                //내용이 긴경우 클릭버튼 상단이동 방지
                var top = ($(this).offset().top) - 180
                if (st > win_hei) {
                    $(window).scrollTop(top)
                }

                sub.hiddenCont();

            });


            function init() {
                wrap.find('.acc_cont').css('display', 'none');
                wrap.find('.acc_btn').removeClass('active');
            }

        })
    },

    modalPopShow: function(obj, wid, topVal = null) { //2024-수요조사-보안평가부 수요조사시스템 IFRAME 높이 문제로 탑값 설정필요

        /** 기존 코드 
        if($('.popup_container').length > 1){
        	$("#commonPopupContainer").removeClass("popup_container");
        }
        var layerWrap = $('.popup_container');
        **/
        var layerWrap = $(obj).parent('.popup_container');
        /************************************** 변경 코드 **/
        var layerBox = $('.layer_box');
        var target = $(obj);
        var str = '<div class="dim"></div>';
        var z_idx = layerBox.css('z-index');

        $('html, body').css('overflow', 'hidden');
        layerWrap.css('display', 'block');

        if (layerWrap.find('.dim').length == 0) {
            layerWrap.append(str);
        } else {
            $('.dim').css('z-index', z_idx + 1);
            target.css('z-index', z_idx + 2);
        }

        $('.dim').fadeIn('fast');
        target.stop().fadeIn('fast').addClass('active');
        target.attr('data-focus', 'on');

        if (wid) {
            target.css('width', wid);
        }
        common.tabmenu(obj);
        modalPosition();

        function modalPosition() {
            var winWid = $(window).outerWidth();
            var winHei = $(window).outerHeight();
            var head_hei = target.find('.pop_head').outerHeight();
            var pop_cont = target.find('.pop_cont');
            var obj_hei = target.outerHeight();
            var obj_wid = target.outerWidth();
            var top = (winHei - obj_hei) / 2;
            var left = (winWid - obj_wid) / 2;

            if (topVal != null) top = topVal; //2024-수요조사-보안평가부 수요조사시스템 IFRAME 높이 문제로 탑설정 고정

            target.css({
                top: top,
                left: left
            });
            target.attr('tabIndex', '0');

            //팝업크기가 화면보다 클때
            if (obj_hei >= winHei) {
                target.css('top', '20px');
                layerWrap.css('overflow-y', 'scroll')
            } else {
                layerWrap.css('overflow-y', '')
            }

            if (obj == '#submitOrg') {
                if (winHei >= 900) {
                    pop_cont.find('.org_list .list_wrap').css('height', pop_cont.height() - 270)
                    pop_cont.find('.org_select .list_wrap').css('height', pop_cont.height() - 140)
                } else {
                    pop_cont.find('.org_list .list_wrap').css('height', '')
                    pop_cont.find('.org_select .list_wrap').css('height', '')
                }
            }

            if (obj == '#orgGroupMdy') {
                if (winHei >= 900) {
                    pop_cont.find('.org_list').css('height', pop_cont.height() - 100)
                } else {
                    pop_cont.find('.org_list').css('height', '')
                }
            }
        }


        $(window).resize(function() {
            modalPosition();
        })
    },

    modalPopHide: function(btn) {
        var target = btn.closest('.layer_box');
        var obj = target.attr('id');
        var layerWrap = $('.popup_container');
        var num = $('.layer_box.active').length;

        $('html, body').css('overflow', '');
        target.removeClass('active').css('display', 'none');

        if (num > 1) {
            $('.dim').css('z-index', '');
        } else {
            layerWrap.hide();
            $('.dim').remove();
        }


        if (target.find('.tab_menu').length > 0) {
            target.find('.tab_menu > li').removeClass('active')
            target.find('.tab_content').css('display', 'none')
        }

    },

    modalPopAutoHide: function(target) {
        var target = $(target);
        var layerWrap = $('.popup_container');
        var num = $('.layer_box.active').length;

        $('html, body').css('overflow', '');
        target.removeClass('active').css('display', 'none');

        if (num > 1) {
            $('.dim').css('z-index', '');
        } else {
            layerWrap.hide();
            $('.dim').remove();
        }


        if (target.find('.tab_menu').length > 0) {
            target.find('.tab_menu > li').removeClass('active')
            target.find('.tab_content').css('display', 'none')
        }

    },

    tooltip: function() {

        $('.help_wrap').filter(function() {
            /* 2019.10.28 수정 : 시작 */
            var typeTEXT = $(this).hasClass('type_text'); //자료제공 > 법령안에서
            if (typeTEXT) {
                return;
            }
            /* 2019.10.28 수정 : 끝 */

            var btn = $('.help_btn');
            btn.mouseenter(function(e) {
                e.stopPropagation();
                var cont = $(this).next('.help_cont');
                var btn_hei = $(this).outerHeight();
                var btn_wid = $(this).outerWidth();
                var cont_hei = cont.outerHeight() / 2;
                var cont_wid = cont.children('.help_txt').outerWidth() / 2;

                if ($(this).closest('.help_wrap').hasClass('bt')) {
                    cont.addClass('show').css({
                        'top': btn_hei + 'px',
                        'margin-left': '-' + cont_wid + 'px'
                    });
                } else {
                    cont.addClass('show').css({
                        'margin-top': '-' + cont_hei + 'px',
                        'margin-left': btn_wid + 'px',
                        'display': 'block'
                    });
                }

            }).mouseleave(function(e) {
                e.stopPropagation();
                $(this).next('.help_cont').removeClass('show');
            });

            var hdiv = $('.help_div');
            hdiv.mouseover(function(e) {
                e.stopPropagation();
                var cont = $(this).next('.help_cont');
                var btn_hei = $(this).outerHeight();
                var btn_wid = $(this).outerWidth();
                var cont_hei = cont.outerHeight() / 2;
                var cont_wid = cont.children('.help_txt').outerWidth() / 2;

                if ($(this).closest('.help_wrap').hasClass('bt')) {
                    cont.addClass('show').css({
                        'top': btn_hei + 'px',
                        'margin-left': '-' + cont_wid + 'px'
                    });
                } else {
                    cont.addClass('show').css({
                        'margin-top': '-' + cont_hei + 'px',
                        'margin-left': btn_wid + 'px',
                        'display': 'block'
                    });
                }

            }).mouseleave(function(e) {
                e.stopPropagation();
                $(this).next('.help_cont').removeClass('show');
            });
        });
    },

    checkAll: function(el) {
        var el_id = el.attr('id');

        if ($('.ck_all').is(':checked')) {

            $('input[id^=' + el_id + ']').prop('checked', true);

        } else {
            $('input[id^=' + el_id + ']').prop('checked', false);
        }
    },

    inputDel: function() {
        $('.st_search').filter(function() {
            var btn = $(this).find('.btn_ddel');
            btn.css('display', 'none')
            $(this).find('input').focus(function() {
                btn.css('display', 'block')
            })
            $(this).find('.btn_ddel').click(function() {
                $(this).prev('input').val('').focus();
            })
        })
    },

    windowPop: function(e, width, height) {
        var url = e.href;
        window.open(url, 'newWindow', 'width=' + width + ', height=' + height + ',top=0, left=0, toolbar=0, status=0, menubar=0, scrollbars=0, resizable=0,');
    },

    windowPop2: function(e, name, width, height) {
        var url = e.href;
        window.open(url, name, 'width=' + width + ', height=' + height + ',top=0, left=0, toolbar=0, status=0, menubar=0, scrollbars=0, resizable=0,');
    }

};

var main = {
    animation: function() {
        $('.section.active').find('[data-ani-effect]').each(function() {
            var ani_obj = $(this);
            var effect = ani_obj.attr('data-ani-effect');
            ani_obj.addClass('animated ' + effect);
        })
    },

    section_third: function() {
        var win_hei = $(window).outerHeight();
        var obj_hei = (win_hei - 142) / 2
        $('.right_area .row_unit').css('height', obj_hei);
    },

    sectionLayerPop: function() {
        $('.section_third').filter(function() {
            var $btnLayer = $('.btn_layer .text'),
                $btnClose = $('.btn_close');

            $btnLayer.on('mouseenter', function() {
                var layerpop = $(this).parent().next('.report_layerPop');
                layerpop.stop().fadeIn(200);
                if (layerpop.hasClass('rm')) {
                    $('.parallels_menu .txt').css('display', 'none')
                }
            })
            $(this).find('.layer_area').on('mouseleave', function() {
                $(this).find('.report_layerPop').stop().fadeOut(200);
                $('.parallels_menu .txt').css('display', '')
            })

            $btnClose.click(function() {
                $(this).closest('.report_layerPop').stop().fadeOut(200);
            })
        });
    },

    ani_section01: function() {
        setTimeout(function() {
            $('.big_txt').addClass('fadeInUp');
        }, 500)
    }
};

var sub = {
    location: function() {
        var $li = $('.location > li'),
            $menu = $('.location > li > a');

        $menu.each(function() {
            if ($(this).next('.smenu').length > 0) {
                $(this).append('<span class="arr"><span>')
            }
        })

        $li.mouseenter(function() {
            $(this).children('a').next('.smenu').css('display', 'block')
        }).mouseleave(function() {
            $(this).children('a').next('.smenu').css('display', 'none')
        })


        var keys = {
            shift: false,
            tab: false
        };

        $(document.body).keydown(function(event) {
            if (event.keyCode == 16) {
                keys["shift"] = true;
            } else if (event.keyCode == 9) {
                keys["tab"] = true;
            }
        })
        $(document.body).keyup(function(event) {
            if (event.keyCode == 16) {
                keys["shift"] = false;
            } else if (event.keyCode == 9) {
                keys["tab"] = false;
            }
        })

        // sub menu의 depth 1이 focusin 되었을 때, depth 2를 display: block & shift + tab 키로 depth 1이 focusin 되었을 때, 해당 depth 1의 마지막 depth 2 메뉴 focus 및 열려있던 다음 depth 2를 display: none 
        $menu.on('focusin', function(e) {
            if ($(this).parent('li').next('li').children('a').next('.smenu').css('display') === 'block' ||
                (($(this).parent('li').next('li').children('a').next('.smenu').css('display') === undefined) && (keys["shift"] && keys["tab"]) && ($(this).next('.smenu').css('display') !== 'block'))
            ) {
                $(this).parent('li').next('li').children('a').next('.smenu').css('display', 'none');

                var $dept2_last = $(this).next('.smenu').find('li > a').last();
                setTimeout(function() {
                    $dept2_last.focus()
                }, 1);
            }
            $(this).next('.smenu').css('display', 'block');

        })

        // 마지막 depth 2에서 tab 키롤 이용해서 다음 메뉴로 넘어갈때, 해당 depth 2를 display: none
        $('.smenu').find('li > a:last').on('focusout', function() {
            if (keys["shift"] && keys["tab"]) {
                return false;
            } else {
                $(this).parents('.smenu').css('display', 'none');
            }
        })

        // sub menu의 btn_home 버튼에 focusin 되었을 때, 나머지 depth 2 메뉴들 display: none
        $('.btn_home').on('focusin', function() {
            $('.smenu').css('display', 'none');
        })
        /**************************************************** 추가 코드 **/
    },

    orgList: function() {
        $('.submitOrg, .orgGroupMdy').filter(function() {
            $(this).find('.btn_open').click(function() {
                if (!$(this).hasClass('active')) {
                    $(this).addClass('active');
                    $(this).closest('.group').next('.group_in').css('display', 'block');
                } else {
                    $(this).removeClass('active');
                    $(this).closest('.group').next('.group_in').css('display', 'none');
                }

            });

            $(this).find('.btn_mdy').click(function() {
                $(this).closest('.group').addClass('on')
                $(this).closest('.group').find('.mdy_input input').prop('disabled', false);
            })
            $(this).find('.btn_save').click(function() {
                $(this).closest('.group').removeClass('on')
                $(this).closest('.group').find('.mdy_input input').prop('disabled', true);
            })
        })
    },

    orgListHeight: function(target) {
        var target = $(target);
        var winHei = $(window).height();

        if (target.hasClass('submitOrg')) {
            var hei = winHei - 480

            target.find('.list_wrap').css('height', hei)

            var tab_wrap_hei = target.find('.tab_wrap').outerHeight();
            var tab_hei = target.find('.tab_content').eq(0).outerHeight();

            target.find('.tab_content').css('height', tab_hei)
            target.find('.org_select .list').css('height', tab_wrap_hei)
        }

    },

    hiddenCont: function() {
        $('.info_assess').each(function() {
            var hei_cont = $(this).find('.cont').height();
            if (hei_cont > 100) {
                $(this).addClass('hidden');
            }
        })

        $('.info_assess').find('.btn_more').click(function() {
            $(this).closest('.info_assess').removeClass('hidden');
        })
    },

    resultReg_hei: function() {
        var $unit = $('.result_reg').find('.box .unit');
        var maxHei;
        var hei = $unit.eq(0).outerHeight(),
            hei2 = $unit.eq(1).outerHeight(),
            hei3 = $unit.eq(2).outerHeight();
        var maxHei = Math.max(hei, hei2, hei3);

        $unit.css('height', maxHei);

    },

    detail_pop: function() {
        $('.pop_wrap').filter(function() {
            $('.pop_menu').on({
                mouseenter: function() {
                    $(this).parent().find('.pop_detail').stop().fadeIn('70');
                },
                mouseleave: function() {
                    $(this).parent().find('.pop_detail').stop().fadeOut('70');
                }
            })
        })
    }

}


$(document).ready(function() {
    common.gnb();
    common.tabmenu('.content_area');
    common.selectmenu();
    common.calendar();
    common.list_sorting();
    common.accordian();
    common.tooltip();
    common.inputDel()
    common.top_menu();
    //main.sectionLayerPop();		로그인시만 실행되므로 주석처리
    main.animation()
    sub.location();
    sub.orgList();
    sub.hiddenCont();
    sub.resultReg_hei();
    sub.detail_pop();


    $(window).scroll(function() {
        var st = $(this).scrollTop();
        if (st > 0) {
            $('.go_top').css('display', 'block');
        }
    })

    $(window).on('load', function() {
        $('.scrollbox').mCustomScrollbar({
            scrollInertia: 200
        });
    })
    $(window).resize(function() {
        $('.scrollbox').mCustomScrollbar('update');
        main.sectionLayerPop();
    })

    // 메뉴 펼치기 20190809
    $('.gnb').filter(function() {
        $(this).find('.btn_gnb').click(function() {
            if (!$(this).hasClass('on')) {
                $(this).addClass('on');
                $(this).next('.gnb_box').stop().slideDown(200)
            } else {
                $(this).removeClass('on');
                $(this).next('.gnb_box').stop().slideUp(200)
            }
        })
    })

    // 검색버튼
    $('.top_search').filter(function() {
        $(this).find('.btn_search').click(function() {
            if (!$(this).hasClass('on')) {
                $(this).addClass('on');
                $(this).next('.input_box').stop().slideDown(200)
            } else {
                $(this).removeClass('on');
                $(this).next('.input_box').stop().slideUp(200)
            }
        })
    })

    $('.compliance').filter(function() {

        $('.status_box').filter(function() {
            var boxTop = $('.compliance .status_box').offset().top;
            var cont_txt = $(this).closest('.content_area').find('.content_title .txt').text();
            var box_tit = $(this).find('h3');
            var status_txt = box_tit.text();

            $(window).scroll(function() {
                var st = $(this).scrollTop();

                if (st >= 0) {
                    $('header').css('position', 'relative');
                    $('#contents').css('padding-top', '0');
                    (st > boxTop) ? fix(): no_fix();
                } else {
                    $('header').css('position', 'fixed');
                    $('#contents').css('padding-top', '142px');
                }

            })

            function fix() {
                $('.status_box').addClass('fix');
                $('.compliance').css('padding-top', '185px');
                if (!$('.compliance .status_box').hasClass('another')) {
                    box_tit.text(cont_txt);
                }
            }

            function no_fix() {
                $('.status_box').removeClass('fix');
                $('.compliance').css('padding-top', '0');
                if (!$('.compliance .status_box').hasClass('another')) {
                    box_tit.text(status_txt);
                    //console.log('test')
                }
            }
        })


        $('.tabst_menu a').click(function(e) {
            e.preventDefault();
            var li = $(this).parent('li');

            $('.tabst_menu li').removeClass('active');
            $('.tabst_menu li').css('border-right', '');
            $(this).parent('li').addClass('active');
            $(this).parent('li').prev('li').css('border-right', 'none');

            var target = $(this).attr('href');
            var scrollTop = $(target).position().top;

            $('.scrollbox').mCustomScrollbar('scrollTo', scrollTop, {
                scrollEasing: "easeOut"
            });

        })

        $('.radio_select').filter(function() {
            var target = $(this).find('label');
            target.click(function() {
                $('.radio_select .selectbox').css('display', 'none');
                $(this).parent('.radiobox').next('.selectbox').css('display', 'inline-block')
            })
        })

    })

    //관련사이트
    $('.footer').filter(function() {
        $(this).find('.btn_link').click(function() {
            $(this).toggleClass('active');
            $(this).next('.link_list').stop().slideToggle(200);
        })
    });

    // 상단 이동
    $('.go_top').click(function() {
        $('html,body').animate({
            scrollTop: 0
        }, 1000);
    })

    // 레이어팝업 닫기
    $('.layer_box .btn_close, .layer_box .layer_close').click(function() {
        common.modalPopHide($(this));
    })


    $('.report').filter(function() {
        $('.btn_setpup').click(function() {
            $(this).css('display', 'none');
            $(this).next('.view_cont').css('display', 'inline-block');
        })
    })

    $('.etc_area').filter(function() {
        $(this).find('.btn_etc').click(function() {
            var target = $(this).children('span')
            var txt = target.text();

            (txt === '기타 의견 보기') ? target.text('기타 의견 닫기'): target.text('기타 의견 보기');
            $(this).closest('.etc_area').toggleClass('view');
            $(this).next('.etc_cont').slideToggle(200);
        })
    })

    $('.window_close').click(function() {
        window.close()
    });

})


/*20190823*/
$(document).ready(function() {
    $(".help_btn_m").click(function() {
        $(".help_cont_m").toggle();
    });
});


/**
 * ---------------------------------
 * 금융보안레그테크시스템 기능개선
 * @2019.10.15 추가
 *  ---------------------------------
 */
$(function() {
    //IE찾기
    var agent = navigator.userAgent.toLowerCase();
    if ((navigator.appName == 'Netscape' && agent.indexOf('trident') != -1) || (agent.indexOf("msie") != -1)) {
        $(document).find('html').addClass('ie')
    }

    //서브 : 정보제공 > 규제 연계분석
    INFO_commentPanel();

    //서브 : 정보제공 > 규제 연계분석 > 자동 분석 키워드
    INFO_keywordResult_Toggle();

    //서브 : 정보제공 > 규제 연계분석 > 툴팁(열리는 위치조정)
    setTimeout(function() {
        INFO_tooltip_typeText();
    }, 1000)

});

/* --- 메인 대시보드 --- */
//탭모양 슬라이더 > 탭버튼
function DASH_tabsSlider(tabName) {
    var _target = $(tabName);
    _target.each(function() {
        var tabA = $(this).find('.item_tab > a');
        tabA.on('click', function() {
            $(this).parent('li').addClass('on');
            $(this).parent('li').siblings().removeClass('on');
        });
    });

    setTimeout(function() {
        MAIN_tabSize();
    }, 300);

    function MAIN_tabSize() {
        var aWidth = _target.find('.item_tab > a');
        aWidth.each(function() {
            var asize = $(this).width();
            $(this).css({
                'width': asize
            })
        });
    }
}

//탭모양 슬라이더 기능 : 주요 부처별 동향
function DASH_lightSlider_Gov() {
    var pagerNum, sceneNum, _btnPREV, _btnNEXT;
    var sliderGov = $("#governmentDepartment").lightSlider({
        pager: true,
        loop: false,
        keyPress: true,
        autoWidth: true,
        slideMargin: 0,
        controls: false,
        onSliderLoad: function(el, pager) {
            $("#governmentDepartment").removeClass('cs_hidden');
            el.parents('.wrap_tab_slider').find('.lSPrev').addClass('stateStart');
        },
        onAfterSlide: function(el, scene) {
            sceneNum = scene + 1;

            _btnPREV = el.parents('.wrap_tab_slider').find('.lSPrev');
            _btnNEXT = el.parents('.wrap_tab_slider').find('.lSNext');

            if (scene > 0) {
                _btnPREV.removeClass('stateStart');
            }
            if (sceneNum < pagerNum || scene > 0) {
                _btnPREV.removeClass('stateStart');
                _btnNEXT.removeClass('stateFinish');
            }
            if (pagerNum === sceneNum) {
                _btnPREV.removeClass('stateStart');
                _btnNEXT.addClass('stateFinish');
            }
            if (scene === 0) {
                _btnPREV.addClass('stateStart');
                _btnNEXT.removeClass('stateFinish');
            }
            //console.log ('scene : ' +  scene )
            //console.log( 'pagerNum' + pagerNum )
        }
    });

    var o_pager = sliderGov.parents('.lSSlideOuter').find('.lSPager > li');
    pagerNum = o_pager.length

    $('.btnsController.typeTrand > .lSPrev').on('click', function() {
        sliderGov.goToPrevSlide();
    });
    $('.btnsController.typeTrand > .lSNext').on('click', function() {
        sliderGov.goToNextSlide();
    });
}

//최신자료 보안뉴스
function DASH_tabNEWS() {
    var _TabMENU = $('#tabMenu_news').find('a.js_tab');
    _TabMENU.on('click', function(e) {
        e.preventDefault();
        var anchorID = $(this).attr('href');
        var ID = $(anchorID);

        $(this).parent('li').addClass('active');
        $(this).parent('li').siblings().removeClass('active');
        $(this).parents('.tab_menu').siblings().removeClass('active');
        $(this).parents('.tabs_menubox').find(ID).addClass('active');
    });
}

function DASH_lightSlider_NEWS() {
    var pagerNum, sceneNum, _btnPREV, _btnNEXT;

    var slider = $('#latestData').lightSlider({
        pager: true,
        loop: false,
        keyPress: true,
        autoWidth: true,
        slideMargin: 10,
        controls: false,
        onSliderLoad: function(el, pager) {
            $("#latestData").removeClass('cs_hidden');
            el.parents('.wrap_hash_slider').find('.lSPrev').addClass('stateStart');
        },
        onAfterSlide: function(el, scene) {
            sceneNum = scene + 1;

            _btnPREV = el.parents('.wrap_hash_slider').find('.lSPrev');
            _btnNEXT = el.parents('.wrap_hash_slider').find('.lSNext');

            if (scene > 0) {
                _btnPREV.removeClass('stateStart');
            }
            if (sceneNum < pagerNum || scene > 0) {
                _btnPREV.removeClass('stateStart');
                _btnNEXT.removeClass('stateFinish');
            }
            if (pagerNum === sceneNum) {
                _btnPREV.removeClass('stateStart');
                _btnNEXT.addClass('stateFinish');
            }
            if (scene === 0) {
                _btnPREV.addClass('stateStart');
                _btnNEXT.removeClass('stateFinish');
            }
            //console.log ('scene : ' +  scene + '/ sceneNum : ' + sceneNum )
            //console.log( 'pagerNum' + pagerNum )
        }
    });
    var o_pager = slider.parents('.lSSlideOuter').find('.lSPager > li');
    pagerNum = o_pager.length

    $('.btnsController.typeHash1 > .lSPrev').on('click', function() {
        slider.goToPrevSlide();
    });
    $('.btnsController.typeHash1 > .lSNext').on('click', function() {
        slider.goToNextSlide();
    });
}


function DASH_lightSlider_NEWS2() {
    var pagerNum, sceneNum, _btnPREV, _btnNEXT;

    var slider = $('#latestData2').lightSlider({
        pager: true,
        loop: false,
        keyPress: true,
        autoWidth: true,
        slideMargin: 10,
        controls: false,
        onSliderLoad: function(el, pager) {
            $("#latestData2").removeClass('cs_hidden');
            el.parents('.wrap_hash_slider').find('.lSPrev').addClass('stateStart');
        },
        onAfterSlide: function(el, scene) {
            sceneNum = scene + 1;

            _btnPREV = el.parents('.wrap_hash_slider').find('.lSPrev');
            _btnNEXT = el.parents('.wrap_hash_slider').find('.lSNext');

            if (scene > 0) {
                _btnPREV.removeClass('stateStart');
            }
            if (sceneNum < pagerNum || scene > 0) {
                _btnPREV.removeClass('stateStart');
                _btnNEXT.removeClass('stateFinish');
            }
            if (pagerNum === sceneNum) {
                _btnPREV.removeClass('stateStart');
                _btnNEXT.addClass('stateFinish');
            }
            if (scene === 0) {
                _btnPREV.addClass('stateStart');
                _btnNEXT.removeClass('stateFinish');
            }
            //console.log ('scene : ' +  scene + '/ sceneNum : ' + sceneNum )
            //console.log( 'pagerNum' + pagerNum )
        }
    });
    var o_pager = slider.parents('.lSSlideOuter').find('.lSPager > li');
    pagerNum = o_pager.length

    $('.btnsController.typeHash2 > .lSPrev').on('click', function() {
        slider.goToPrevSlide();
    });
    $('.btnsController.typeHash2 > .lSNext').on('click', function() {
        slider.goToNextSlide();
    });
}

/*가이드 추가 */
function DASH_lightSlider_NEWS3() {
    var pagerNum, sceneNum, _btnPREV, _btnNEXT;

    var slider = $('#latestData3').lightSlider({
        pager: true,
        loop: false,
        keyPress: true,
        autoWidth: true,
        slideMargin: 10,
        controls: false,
        onSliderLoad: function(el, pager) {
            $("#latestData3").removeClass('cs_hidden');
            el.parents('.wrap_hash_slider').find('.lSPrev').addClass('stateStart');
        },
        onAfterSlide: function(el, scene) {
            sceneNum = scene + 1;

            _btnPREV = el.parents('.wrap_hash_slider').find('.lSPrev');
            _btnNEXT = el.parents('.wrap_hash_slider').find('.lSNext');

            if (scene > 0) {
                _btnPREV.removeClass('stateStart');
            }
            if (sceneNum < pagerNum || scene > 0) {
                _btnPREV.removeClass('stateStart');
                _btnNEXT.removeClass('stateFinish');
            }
            if (pagerNum === sceneNum) {
                _btnPREV.removeClass('stateStart');
                _btnNEXT.addClass('stateFinish');
            }
            if (scene === 0) {
                _btnPREV.addClass('stateStart');
                _btnNEXT.removeClass('stateFinish');
            }
            //console.log ('scene : ' +  scene + '/ sceneNum : ' + sceneNum )
            //console.log( 'pagerNum' + pagerNum )
        }
    });
    var o_pager = slider.parents('.lSSlideOuter').find('.lSPager > li');
    pagerNum = o_pager.length

    $('.btnsController.typeHash3 > .lSPrev').on('click', function() {
        slider.goToPrevSlide();
    });
    $('.btnsController.typeHash3 > .lSNext').on('click', function() {
        slider.goToNextSlide();
    });
}

/*가이드 추가 */
function DASH_lightSlider_NEWS4() {
    var pagerNum, sceneNum, _btnPREV, _btnNEXT;

    var slider = $('#latestData4').lightSlider({
        pager: true,
        loop: false,
        keyPress: true,
        autoWidth: true,
        slideMargin: 10,
        controls: false,
        onSliderLoad: function(el, pager) {
            $("#latestData4").removeClass('cs_hidden');
            el.parents('.wrap_hash_slider').find('.lSPrev').addClass('stateStart');
        },
        onAfterSlide: function(el, scene) {
            sceneNum = scene + 1;

            _btnPREV = el.parents('.wrap_hash_slider').find('.lSPrev');
            _btnNEXT = el.parents('.wrap_hash_slider').find('.lSNext');

            if (scene > 0) {
                _btnPREV.removeClass('stateStart');
            }
            if (sceneNum < pagerNum || scene > 0) {
                _btnPREV.removeClass('stateStart');
                _btnNEXT.removeClass('stateFinish');
            }
            if (pagerNum === sceneNum) {
                _btnPREV.removeClass('stateStart');
                _btnNEXT.addClass('stateFinish');
            }
            if (scene === 0) {
                _btnPREV.addClass('stateStart');
                _btnNEXT.removeClass('stateFinish');
            }
            //console.log ('scene : ' +  scene + '/ sceneNum : ' + sceneNum )
            //console.log( 'pagerNum' + pagerNum )
        }
    });
    var o_pager = slider.parents('.lSSlideOuter').find('.lSPager > li');
    pagerNum = o_pager.length

    $('.btnsController.typeHash4 > .lSPrev').on('click', function() {
        slider.goToPrevSlide();
    });
    $('.btnsController.typeHash4 > .lSNext').on('click', function() {
        slider.goToNextSlide();
    });
}


//컴플라이언스 툴팁
function DASH_compliance() {
    var _calendar_moreInfo = $('.calendar_table .js_show_info');
    _calendar_moreInfo.each(function() {
        $(this).off('click.cp').on('click.cp', function() {
            var $parent = $(this).parent('td');
            var $helpCon = $parent.find('.tooltip_wrap > .help_cont');

            if ($parent.hasClass('on')) {
                $parent.removeClass('on');
                $parent.find('.tooltip_wrap > .help_cont').removeClass('show');
            } else {
                $(this).parents('.calendar_table').find('td.on').removeClass('on');
                $parent.addClass('on');

                $(this).parents().find('.tooltip_wrap > .help_cont').removeClass('show');
                $parent.find('.tooltip_wrap > .help_cont').addClass('show');
            }

            //닫기
            var closeBtn = $helpCon.find('.btn_close_cont');
            closeBtn.on('click', function() {
                $(this).parents('.help_cont').removeClass('show');
                $(this).closest('td').removeClass('on');
            });
        });
    });
}

/* --- 서브 --- */
//정보제공 > 규제 연계분석
function INFO_commentPanel() {
    if (!$('.btn_ctrl_panel').length) return;

    $('.btn_ctrl_panel').off('click').on('click', function() {
        var _ts = $(this);
        var _text = _ts.find('>span');

        //열린상태
        if (_ts.hasClass('opened')) {
            _ts.removeClass('opened').addClass('closed');
            _ts.parents('.section_right').removeClass('opened').addClass('closed');
            _text.text('코멘트 보기');
        }

        //닫힌상태
        else {
            _ts.addClass('opened').removeClass('closed');
            _ts.parents('.section_right').addClass('opened').removeClass('closed');
            _text.text('코멘트 숨기기');
        }
    });
}

//정보제공 > 규제 연계분석 > 자동 분석 키워드
function INFO_keywordResult_Toggle() {
    if (!$('.result_sub_group').length) return;

    var wrapperPara, sizeParagraph;

    function txtSentence() {
        $('.para_list .txt_sentence').each(function() {
            sizeParagraph = $(this).width();
            wrapperPara = $(this).parents('.keyword_result').width();
            //console.log('paragraph : ' + sizeParagraph);
            //console.log('wrapperPara : ' + wrapperPara);

            if (sizeParagraph > wrapperPara) {
                $(this).siblings('.btn_tgg').show();
                $(this).addClass('ellipsis');
            } else if (sizeParagraph < wrapperPara) {
                $(this).siblings('.btn_tgg').hide();
            }
        });
    };

    setTimeout(function() {
        txtSentence();
    }, 200);

    $('.result_sub_group .btn_tgg').each(function() {
        var _btn = $(this);
        var txtSentence = $(this).siblings('.txt_sentence');

        _btn.on('click', function() {
            if ($(this).hasClass('opened')) {
                $(this).removeClass('opened');
                $(this).find('>span').text('펼치기');
                txtSentence.removeClass('overflow');
            } else {
                $(this).addClass('opened');
                $(this).find('>span').text('닫기');
                txtSentence.addClass('overflow');
            }
        });
    });
}

//정보제공 > 규제 연계분석 > 툴팁(열리는 위치조정)
function INFO_tooltip_typeText() {
    var guideTEXT = $('.help_wrap.type_text');
    if (!guideTEXT.length) return;

    var guideBTN = guideTEXT.find('.help_btn');
    guideBTN.each(function() {
        var cont = $(this).next('.help_cont');
        cont.attr('style', '');
        cont.css({
            'left': 0,
        });
        var areaLeftPos = $(".sec_texts").offset().left + 20;
        var areaWidth = $("#law_conts_container").width() - 36; //36은 padding값
        var tooltipWidth = cont.width();
        var topPos = $(this).outerHeight() - 12;
        var limitContsPos = areaLeftPos + areaWidth - tooltipWidth;
        var leftPos = $(this).offset().left;
        var chg_left = 0;

        if (leftPos > limitContsPos) {
            //오른쪽 범위를 넘어 서는 경우
            chg_left = (guideBTN.position().left) - 420 + $(this).width();

            //console.log(areaLeftPos + "/" + leftPos + "/" + chg_left + "/" + $(this).html());
            //console.log(leftPos - chg_left)

            if (areaLeftPos > (chg_left + leftPos)) {
                //왼쪽 범위를 넘어서는 경우
                chg_left = areaLeftPos - leftPos + ($(this).width() / 2);
            }
        }

        cont.css({
            'top': topPos,
            'left': chg_left,
        });

        $(this).on('mouseenter', function(e) {
            $('.help_cont').each(function() {
                if ($(this).hasClass("show")) {
                    $(this).removeClass('show');
                }
            });

            cont.addClass('show');
        });

        //kcg 
        $('.help_cont').on('mouseleave', function(e) {
            cont.removeClass('show');
        });

    });

}
//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
// 2022 금융보안 레그테크 포털 개인정보 보호 강화 관련 시스템 도입 START
//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////

// 새로 만든 화면 여부
let comm_isRenewal_2022 = false;
let comm_url_prifix = '';
/**
 * 메시지 통일화
 * n : 메시지 번호
 * t1,t2,t3 : 추가 메시지
 * 100 : 경고창
 * 200 : 확인창
 * 300 : 화면 표출 메시지
 * 400 : 기타
 *   10 : info
 *   20 : waring
 *   30 : error
 *   40 : etc.
 */
const comm_msg = function(n, t1, t2, t3) {
    let msg = '';

    switch (n) {
        case 111:
            msg = '처리가 완료 되었습니다.';
            break;
        case 112:
            msg = '요청이 완료 되었습니다.';
            break;
        case 131:
            msg = '조회에 실패하였습니다.';
            break;
        case 132:
            msg = '처리된 항목이 없습니다.\n관리자에게 문의 바랍니다.';
            break;
        case 133:
            msg = '저장에 실패하였습니다.';
            break;
        case 121:
            msg = '선택된 행이 없습니다.';
            break;
        case 122:
            msg = '처리된 항목이 없습니다.\n화면을 새로 고침 후 다시 요청 바랍니다.';
            break;
        case 211:
            msg = '선택된 항목(들)을 ' + t1 + ' 처리 하시겠습니까?';
            break;
        case 3:
            msg = '';
            break;
        default:
            break;
    }

    return msg;
};

$(document).ready(function() {
    comm_events();
});

function comm_events() {

    if (comm_isRenewal_2022) {
        $('div .paging_area').on('click', 'li', function(e) {
            //let shouldReFind = true;
            let shouldReMakeHtml = false;
            const $div = $(this).closest('div.paging_area');

            let combineWith = $div.attr('data-combineWith');
            const currentPageNo = parseInt($div.find('li.on a').text());
            const currentLastPageNoBox = parseInt($div.find('li.link_page:last() a').text());

            const pageNoBoxCnt = Math.ceil(parseInt($div.attr('data-totalCnt')) / parseInt($div.attr('data-pagingViewRows')));
            let setPageNo = 1;

            if ($(this).hasClass('btn_first')) {
                setPageNo = 1;
            } else if ($(this).hasClass('btn_prev')) {
                setPageNo = currentPageNo > 1 ? currentPageNo - 1 : 1;
            } else if ($(this).hasClass('btn_next')) {
                setPageNo = currentPageNo < pageNoBoxCnt ? currentPageNo + 1 : pageNoBoxCnt;
            } else if ($(this).hasClass('btn_last')) {
                setPageNo = pageNoBoxCnt;
            } else if ($(this).hasClass('paging_num')) {
                $(this).parent().find('li').removeClass('on');
                $(this).addClass('on');
                setPageNo = parseInt($(this).find('a').text());
            }

            let excuteFn = new Function(combineWith + '(' + setPageNo + ')')();
        });

    }
}

function comm_isBlank(s) {
    if (s == undefined || s == null || (s + '').trim() == '' || (s != null && typeof s == 'object' && !Object.keys(s).length)) {
        return true;
    } else {
        return false;
    }
}

function comm_isNotBlank(s) {
    return !comm_isBlank(s);
}

function comm_trim(s) {
    if (comm_isNotBlank(s)) {
        return s.toString().trim();
    }
    return '';
}

function comm_nvl(s1, s2) {
    return comm_isNotBlank(s1) ? s1 : s2;
}

function comm_nvl2(s1, s2, s3) {
    return comm_isNotBlank(s1) ? s2 : s3;
}

function comm_comma(s) {
    return (s + '').replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}


/*************************************************************************
 * settings
 ************************************************************************/

/**
 * 
 * @param $checkAll			: 전체 체크 박스
 * @param $checkboxes		: 제어 대상 체크 박스
 * @param $parentElement	: 제어 대상 체크 박스의 부모 요소
 * @returns
 * @note 		inner HTML 을 사용하는 경우 $checkboxes 를 null로 할당하고 $parentElement 를 활용해야 함
 */
function comm_setEvent_checkBox($checkAll, $checkboxes, $parentElement) {
    if (comm_isNotBlank($checkboxes)) {
        // inner HTML 을 사용하지 않는 경우
        // 전체 체크 박스 제어
        $checkAll.on('change', function() {
            $checkboxes.prop('checked', $(this).prop('checked'));
        });

        // 전체를 제외한 체크 박스 값에 따른 전체 체크 박스 제어
        $checkboxes.on('change', function() {
            $checkAll.prop('checked',
                ($checkboxes.not(':checked').length == 0 ? true : false)
            );
        });
    } else {
        // inner HTML 을 사용하는 경우
        // 전체 체크 박스 제어
        $checkAll.on('change', function() {
            $parentElement.find('input[type=checkbox]').prop('checked', $(this).prop('checked'));
        });

        // 전체를 제외한 체크 박스 값에 따른 전체 체크 박스 제어
        $parentElement.on('change', 'input[type=checkbox]', function() {
            $checkAll.prop('checked',
                ($parentElement.find('input[type=checkbox]').not(':checked').length == 0 ? true : false)
            );
        });
    }
    $checkAll.trigger('change');
}

/*************************************************************************
 * paging
 ************************************************************************/
let pagingHtml_priffix = `
	<span id="pagination-demo" class="pagination-sm inner_paging">
    <ul class="pagination">
        <li class="btn_paging btn_first disabled">
            <a href="#" class="page-link">
                <span class="btn_first">첫페이지 </span>
            </a>
        </li>
        <li class="btn_paging btn_prev disabled">
        	<a href="#" class="page-link">
        		<span class="btn_prev">이전</span>
        	</a>
        </li>
`;

let pagingHtml_suffix = `
        <li class="btn_paging btn_next">
            <a href="#" class="page-link">
                <span class="btn_next">다음</span>
            </a>
        </li>
        <li class="btn_paging btn_last">
            <a href="#" class="page-link">
                <span class="btn_last">마지막페이지 </span>
            </a>
        </li>
    </ul>
</span>
`;

let pagingHtml_pageNoBox = function(i, classOn) {
    return '<li class="paging_num ' + classOn + '"><a href="#" class="paging_num">' + i + '</a></li>';
}

/**
 * 페이징 박스 그리기
 * @param targetNo				: 페이징 최 상단 div-tag id의 suffix  e.g) 01 =  paging01
 * @param totalCnt					: 총 건 수
 * @param pagingViewRows		: 한 페이지에 보이는 행 수
 * @param pagingCurrentPage	: 선택된 페이지 수
 * @returns
 */
function comm_paging_createHtml(targetNo, totalCnt, pagingViewRows, pagingCurrentPage) {
    const maxPageNoBox = 10;
    let pageNoBoxCnt = Math.ceil(totalCnt / pagingViewRows);
    let setPageNoBox = Math.ceil(parseInt(pagingCurrentPage) / 10) * 10 - 9;
    let pagingHtml = pagingHtml_priffix;

    let i = 1;
    while (maxPageNoBox >= i) {
        pagingHtml += pagingHtml_pageNoBox(setPageNoBox, (setPageNoBox == pagingCurrentPage ? 'on' : ''));
        setPageNoBox++;
        i++;
        if (pageNoBoxCnt < setPageNoBox) {
            break;
        }
    }
    pagingHtml += pagingHtml_suffix;


    $('#paging' + targetNo).attr('data-totalCnt', totalCnt);
    $('#paging' + targetNo).attr('data-pagingViewRows', pagingViewRows);
    $('#paging' + targetNo).html(pagingHtml);
    $('#spanTotalCnt' + targetNo).text(comm_comma(totalCnt));

}

/**
 * 결과가 없을 경우 데이터가 없을을 테이블에 표현
 * @param $target			: tbody의 위치
 * @param columnCnt		: colspan을 위한 값
 * @param pagingDivNo	: 페이징 최 상단 div-tag id의 suffix  e.g) 01 =  paging01
 * @returns
 */
function comm_paging_emptyRow($target, columnCnt, pagingDivNo) {
    $target.html('<td colspan="' + columnCnt + '">데이터가 없습니다.</td>');
    $('#spanTotalCnt' + pagingDivNo).text('0');
    $('#paging' + pagingDivNo).empty();
}

/*************************************************************************
 * date
 ************************************************************************/
/**
 d: date
 f : yyyy.mm.dd. hh.mi.ss
 */
function comm_formatDate(s, f) {
    let result = '';
    let date = new Date();

    if (comm_isNotBlank(s)) {
        if (typeof s.getMonth === 'function') {
            date = s;
        } else if (typeof s === 'string') {
            if (s.includes('/') || s.includes('.')) {
                date = new Date(s);
            } else {
                let str = '';
                str = s.replace(/[^0-9]/gi, '');
                date = comm_numToDate(str);
            }
        } else if (typeof s === 'number') {
            if (s.toString().length == 13) {
                date = new Date(s);
            } else {
                date = comm_numToDate(str);
            }
        } else {
            date = new Date();
        }
    }
    if (typeof date.getMonth === 'function') {
        result = f.toLowerCase();
        result = result.replace('yyyy', date.getFullYear());
        result = result.replace('mm', ((date.getMonth() + 1) + '').padStart(2, '0'));
        result = result.replace('dd', (date.getDate() + '').padStart(2, '0'));
        result = result.replace('hh', (date.getHours() + '').padStart(2, '0'));
        result = result.replace('mi', (date.getMinutes() + '').padStart(2, '0'));
        result = result.replace('ss', (date.getSeconds() + '').padStart(2, '0'));
    }

    return result;
}

function comm_numToDate(n) {
    let str = n.toString();
    let yyyy = '';
    let mm = '';
    let dd = '';
    let hh = '';
    let mi = '';
    let ss = '';

    switch (str.length) {
        case 14:
            ss = str.substr(12, 2);
        case 12:
            mi = str.substr(10, 2);
        case 10:
            hh = str.substr(8, 2);
        case 8:
            dd = str.substr(6, 2);
        case 6:
            mm = parseInt(str.substr(4, 2)) - 1;
        case 4:
            yyyy = str.substr(0, 4);
    }

    return new Date(yyyy, mm, dd, hh, mi, ss);
}

/*************************************************************************
 * ajax
 ************************************************************************/
/**
 * 코드 테이블의 부모 코드로 checkbox 혹은 option 만들기
 * @param pCode : COMMON_CODE.CODE_PARENT
 * @param $target : 대상 객체
 * @param isCheckbox	: true=checkbox , false=selectbox
 * @param hasEmptyDefault : [checkbox 전체] or [option 선택]
 * @returns innerHtml setting
 */
function comm_setCodeList(pCode, $target, isCheckbox, hasEmptyDefault, isEmptyTextAll) {

    $.ajax({
        async: false,
        type: 'GET',
        url: '/common/code/selectCodeListByLevelJson',
        dataType: 'json',
        data: {
            'codeValue': pCode
        },
        success: function(data) {
            let innerHtml = '';
            if (data.length > 0) {
                let emptyTextValue = isEmptyTextAll ? '전체' : '선택';

                if (isCheckbox) {
                    innerHtml = hasEmptyDefault ?
                        `<input type="checkbox" id="checkAll_${pCode}" name="checkbox_${pCode}" value="" class="ml10" checked/>
							 <label for="checkAll_${pCode}">${emptyTextValue}</label>` :
                        '';
                    const checkProp = hasEmptyDefault ? '' : 'checked';
                    $.each(data, function(i, v) {
                        innerHtml += `<input type="checkbox" id="checkbox_${v.codeValue}" name="checkbox_${pCode}" value="${v.codeValue}" class="ml10" ${checkProp}/>
							 <label for="checkbox_${v.codeValue}">${v.codeName}</label>`;
                    });
                } else {
                    innerHtml = hasEmptyDefault ?
                        `<option value="">${emptyTextValue}</option>` :
                        '';
                    $.each(data, function(i, v) {
                        innerHtml += `<option value="${v.codeValue}">${v.codeName}</option>`;
                    });
                }
            }
            $target.html('');
            $target.html(innerHtml);
            if (isCheckbox) {
                comm_setEvent_checkBox($('#checkAll_' + pCode), $('input[name="checkbox_' + pCode + '"]').not(':eq(0)'), null);
                $('input[name="checkbox_' + pCode + '"]').trigger('change');
            }
        },
        error: function(data) {
            return false;
        }
    });

}


//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
// 2022 금융보안 레그테크 포털 개인정보 보호 강화 관련 시스템 도입 END
//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////