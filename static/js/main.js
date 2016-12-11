var
arg = {
	'font-size':'2em',
	'transform':'rotate(5deg)'
},
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
	});
});