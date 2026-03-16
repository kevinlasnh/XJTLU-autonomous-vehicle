#include <linux/module.h>
#define INCLUDE_VERMAGIC
#include <linux/build-salt.h>
#include <linux/elfnote-lto.h>
#include <linux/vermagic.h>
#include <linux/compiler.h>

BUILD_SALT;
BUILD_LTO_INFO;

MODULE_INFO(vermagic, VERMAGIC_STRING);
MODULE_INFO(name, KBUILD_MODNAME);

__visible struct module __this_module
__section(".gnu.linkonce.this_module") = {
	.name = KBUILD_MODNAME,
	.init = init_module,
#ifdef CONFIG_MODULE_UNLOAD
	.exit = cleanup_module,
#endif
	.arch = MODULE_ARCH_INIT,
};

#ifdef CONFIG_RETPOLINE
MODULE_INFO(retpoline, "Y");
#endif

static const struct modversion_info ____versions[]
__used __section("__versions") = {
	{ 0x25f8bfc1, "module_layout" },
	{ 0x8e17b3ae, "idr_destroy" },
	{ 0xd81a27d7, "usb_deregister" },
	{ 0x92997ed8, "_printk" },
	{ 0x2d22efc2, "tty_driver_kref_put" },
	{ 0x4c1ebf57, "tty_unregister_driver" },
	{ 0x83f07a09, "usb_register_driver" },
	{ 0xc7665c72, "tty_register_driver" },
	{ 0x67b27ec1, "tty_std_termios" },
	{ 0x7757761, "__tty_alloc_driver" },
	{ 0x6cbbfc54, "__arch_copy_to_user" },
	{ 0x908e5601, "cpu_hwcaps" },
	{ 0x37110088, "remove_wait_queue" },
	{ 0x1000e51, "schedule" },
	{ 0x4afb2238, "add_wait_queue" },
	{ 0xaad8c7d6, "default_wake_function" },
	{ 0xc6cbbc89, "capable" },
	{ 0x12a4e128, "__arch_copy_from_user" },
	{ 0x4c1a2642, "tty_flip_buffer_push" },
	{ 0x5e2f70f6, "tty_insert_flip_string_fixed_flag" },
	{ 0xc2b257a8, "tty_port_register_device" },
	{ 0x30f3d94d, "usb_get_intf" },
	{ 0x6a984990, "usb_driver_claim_interface" },
	{ 0x7504e97d, "usb_alloc_urb" },
	{ 0xa72c0785, "usb_alloc_coherent" },
	{ 0xdcb764ad, "memset" },
	{ 0xeb545aab, "tty_port_init" },
	{ 0xcefb0c9f, "__mutex_init" },
	{ 0xd9a5ea54, "__init_waitqueue_head" },
	{ 0xb8f11603, "idr_alloc" },
	{ 0xed1477f7, "usb_ifnum_to_if" },
	{ 0x652f7777, "usb_put_intf" },
	{ 0x7665a95b, "idr_remove" },
	{ 0x3ea1b6e4, "__stack_chk_fail" },
	{ 0x409873e3, "tty_termios_baud_rate" },
	{ 0x6c257ac0, "tty_termios_hw_change" },
	{ 0xc5b6f236, "queue_work_on" },
	{ 0x2d3385d3, "system_wq" },
	{ 0x296695f, "refcount_warn_saturate" },
	{ 0xbb62e0ae, "tty_standard_install" },
	{ 0x69f38847, "cpu_hwcap_keys" },
	{ 0x14b89635, "arm64_const_caps_ready" },
	{ 0x20978fb9, "idr_find" },
	{ 0x37a0cba, "kfree" },
	{ 0xd58d4b67, "kmem_cache_alloc_trace" },
	{ 0xc1c7e6c0, "kmalloc_caches" },
	{ 0x27a2116c, "usb_control_msg" },
	{ 0x1667ecb9, "usb_autopm_get_interface" },
	{ 0xcc9f61b7, "tty_port_open" },
	{ 0x10452d22, "tty_port_close" },
	{ 0x802f71a3, "usb_anchor_urb" },
	{ 0xa544ade4, "usb_autopm_get_interface_async" },
	{ 0x4829a47e, "memcpy" },
	{ 0xdf73ce49, "tty_port_hangup" },
	{ 0x1995c275, "tty_port_tty_wakeup" },
	{ 0x9eabcdb, "usb_get_from_anchor" },
	{ 0xd2cdc483, "usb_autopm_put_interface" },
	{ 0xf1bac7db, "usb_autopm_get_interface_no_resume" },
	{ 0x48962926, "tty_port_tty_hangup" },
	{ 0x6ebe366f, "ktime_get_mono_fast_ns" },
	{ 0x85fd2dbe, "_dev_info" },
	{ 0xc442c16a, "usb_driver_release_interface" },
	{ 0x8abcf63a, "usb_free_coherent" },
	{ 0x865f28c0, "usb_free_urb" },
	{ 0x22e0737c, "tty_unregister_device" },
	{ 0x549ff25b, "tty_kref_put" },
	{ 0xeb6ca7f0, "tty_vhangup" },
	{ 0xf093ec8a, "tty_port_tty_get" },
	{ 0x3213f038, "mutex_unlock" },
	{ 0x3eeb2322, "__wake_up" },
	{ 0x4dfa8d4b, "mutex_lock" },
	{ 0xbdff5c7e, "tty_port_put" },
	{ 0x4b750f53, "_raw_spin_unlock_irq" },
	{ 0x8427cc7b, "_raw_spin_lock_irq" },
	{ 0x3c12dfe, "cancel_work_sync" },
	{ 0xd4bacb8, "usb_kill_urb" },
	{ 0x4b0a3f52, "gic_nonsecure_priorities" },
	{ 0x45642a17, "usb_autopm_put_interface_async" },
	{ 0x89c9a638, "_dev_err" },
	{ 0x46834faf, "usb_submit_urb" },
	{ 0xd35cce70, "_raw_spin_unlock_irqrestore" },
	{ 0x34db050b, "_raw_spin_lock_irqsave" },
	{ 0x1fdc7df2, "_mcount" },
};

MODULE_INFO(depends, "");

MODULE_ALIAS("usb:v1A86p7523d*dc*dsc*dp*ic*isc*ip*in*");
MODULE_ALIAS("usb:v1A86p7522d*dc*dsc*dp*ic*isc*ip*in*");
MODULE_ALIAS("usb:v1A86p5523d*dc*dsc*dp*ic*isc*ip*in*");
MODULE_ALIAS("usb:v1A86pE523d*dc*dsc*dp*ic*isc*ip*in*");
MODULE_ALIAS("usb:v4348p5523d*dc*dsc*dp*ic*isc*ip*in*");

MODULE_INFO(srcversion, "28C2A78207A7AB3BFC8DC96");
