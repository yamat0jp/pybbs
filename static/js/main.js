var
arg = {
	'font-size':'2em',
	'transform':'rotate(5deg)'
};
narg = {
	'font-size':'initial',
	'transform':'initial'
};

$(function(){
	$('div').on('click',function(){
		$(this).css(arg);
	})
	.on('mouseout',function(){
		$(this).css(narg);
	})
	.on('mousemove',function(){
		$(this).css(narg);
	});
});
$(document).ready(function(){
	$('.livepreview').livePreview({
	    trigger: 'hover',
	    viewWidth: 300,  
	    viewHeight: 200,  
	    targetWidth: 1000,  
	    targetHeight: 800,  
	    scale: '0.5', 
	    offset: 50,
	    position: 'left'
	});
});