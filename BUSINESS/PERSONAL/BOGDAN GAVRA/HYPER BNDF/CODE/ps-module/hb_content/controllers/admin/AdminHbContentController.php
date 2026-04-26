<?php
if (!defined('_PS_VERSION_')) exit;

class AdminHbContentController extends ModuleAdminController
{
    public function __construct()
    {
        $this->bootstrap = true;
        parent::__construct();
        $this->meta_title = 'Conținut Site — HYPER BNDF';
    }

    public function initContent()
    {
        $this->content = $this->renderForm();
        parent::initContent();
    }

    public function renderForm()
    {
        $sections = [
            'Homepage — Hero' => [
                'HB_HERO_EYEBROW', 'HB_HERO_TITLE', 'HB_HERO_SUBTITLE',
                'HB_HERO_TEXT', 'HB_HERO_BTN_CATALOG', 'HB_HERO_BTN_PACKAGES',
            ],
            'Homepage — Banner CTA' => [
                'HB_CTA_TITLE', 'HB_CTA_TEXT', 'HB_CTA_BTN',
            ],
            'Homepage — Strip Pachete' => [
                'HB_PKG_LABEL', 'HB_PKG_TEXT', 'HB_PKG_BTN',
            ],
            'Catalog Produse' => [
                'HB_CAT_TITLE', 'HB_CAT_SUBTITLE', 'HB_CAT_TEXT',
            ],
        ];

        $form_inputs = [];
        foreach ($sections as $legend => $keys) {
            $inputs = [];
            foreach ($keys as $key) {
                $def = Hb_Content::FIELDS[$key];
                $input = [
                    'name'  => $key,
                    'label' => $def['label'],
                    'type'  => $def['type'] === 'textarea' ? 'textarea' : 'text',
                    'lang'  => false,
                    'cols'  => 60,
                    'rows'  => 3,
                ];
                $inputs[] = $input;
            }
            $form_inputs[] = [
                'form' => [
                    'legend' => ['title' => $legend, 'icon' => 'icon-pencil'],
                    'input'  => $inputs,
                    'submit' => ['title' => 'Salvează', 'class' => 'btn btn-default pull-right'],
                ],
            ];
        }

        $helper = new HelperForm();
        $helper->module = $this->module;
        $helper->name_controller = $this->controller_name;
        $helper->token = Tools::getAdminTokenLite($this->controller_name);
        $helper->currentIndex = AdminController::$currentIndex . '&configure=' . $this->module->name;
        $helper->submit_action = 'saveHbContent';
        $helper->show_toolbar = false;

        foreach (array_keys(Hb_Content::FIELDS) as $key) {
            $helper->fields_value[$key] = Configuration::get($key);
        }

        return $helper->generateForm($form_inputs);
    }

    public function postProcess()
    {
        if (Tools::isSubmit('saveHbContent')) {
            foreach (array_keys(Hb_Content::FIELDS) as $key) {
                if (Tools::getIsset($key)) {
                    Configuration::updateValue($key, Tools::getValue($key));
                }
            }
            Hb_Content::writeJson();
            $this->confirmations[] = 'Conținutul a fost salvat și publicat pe site.';
        }
        parent::postProcess();
    }
}
