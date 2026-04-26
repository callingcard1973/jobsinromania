<?php
if (!defined('_PS_VERSION_')) exit;

class Hb_Content extends Module
{
    const FIELDS = [
        'HB_HERO_EYEBROW'       => ['label' => 'Tagline mic (deasupra titlului)',          'type' => 'text'],
        'HB_HERO_TITLE'         => ['label' => 'Titlu H1 — linia 1',                       'type' => 'text'],
        'HB_HERO_SUBTITLE'      => ['label' => 'Titlu H1 — linia 2 (verde)',               'type' => 'text'],
        'HB_HERO_TEXT'          => ['label' => 'Text sub titlu',                            'type' => 'textarea'],
        'HB_HERO_BTN_CATALOG'   => ['label' => 'Buton principal (catalog)',                 'type' => 'text'],
        'HB_HERO_BTN_PACKAGES'  => ['label' => 'Buton pachete',                             'type' => 'text'],
        'HB_CTA_TITLE'          => ['label' => 'Banner CTA — titlu',                        'type' => 'text'],
        'HB_CTA_TEXT'           => ['label' => 'Banner CTA — text',                         'type' => 'textarea'],
        'HB_CTA_BTN'            => ['label' => 'Banner CTA — buton',                        'type' => 'text'],
        'HB_PKG_LABEL'          => ['label' => 'Strip pachete — titlu',                     'type' => 'text'],
        'HB_PKG_TEXT'           => ['label' => 'Strip pachete — text',                      'type' => 'textarea'],
        'HB_PKG_BTN'            => ['label' => 'Strip pachete — buton',                     'type' => 'text'],
        'HB_CAT_TITLE'          => ['label' => 'Catalog — titlu H1 linia 1',               'type' => 'text'],
        'HB_CAT_SUBTITLE'       => ['label' => 'Catalog — titlu H1 linia 2',               'type' => 'text'],
        'HB_CAT_TEXT'           => ['label' => 'Catalog — text sub titlu',                  'type' => 'textarea'],
    ];

    const DEFAULTS = [
        'HB_HERO_EYEBROW'      => 'Echipamente certificate CE · Partener AVP Park Turcia',
        'HB_HERO_TITLE'        => 'Locuri de joacă',
        'HB_HERO_SUBTITLE'     => 'pentru comunitatea ta',
        'HB_HERO_TEXT'         => '226 produse — structuri de joacă, leagăne, fitness exterior, mobilier urban. Oferte personalizate pentru primării și instituții publice.',
        'HB_HERO_BTN_CATALOG'  => 'Vezi catalogul',
        'HB_HERO_BTN_PACKAGES' => 'Pachete & Prețuri',
        'HB_CTA_TITLE'         => 'AUDIT TEREN GRATUIT',
        'HB_CTA_TEXT'          => 'Venim la tine, măsurăm terenul și îți lăsăm un proiect orientativ fără niciun cost.',
        'HB_CTA_BTN'           => 'Programează acum →',
        'HB_PKG_LABEL'         => 'Pachete complete cu prețuri fixe',
        'HB_PKG_TEXT'          => '3 pachete gata configurate — de la 18.000 RON · montaj ISCIR inclus · documentație SEAP completă',
        'HB_PKG_BTN'           => 'Vezi pachete și prețuri →',
        'HB_CAT_TITLE'         => 'Catalog',
        'HB_CAT_SUBTITLE'      => 'Echipamente',
        'HB_CAT_TEXT'          => '226 produse AVP Park — structuri de joacă, leagăne, echipamente fitness exterior',
    ];

    public function __construct()
    {
        $this->name = 'hb_content';
        $this->tab = 'administration';
        $this->version = '1.0.0';
        $this->author = 'HYPER BNDF';
        $this->need_instance = 0;
        parent::__construct();
        $this->displayName = 'Conținut Site';
        $this->description = 'Editează textele afișate pe hyperbndf.com';
    }

    public function install()
    {
        foreach (self::DEFAULTS as $key => $val) {
            Configuration::updateValue($key, $val);
        }
        $this->writeJson();

        $tab = new Tab();
        $tab->class_name = 'AdminHbContent';
        $tab->module = $this->name;
        $tab->id_parent = (int) Tab::getIdFromClassName('AdminParentModulesSf');
        $tab->icon = 'edit';
        foreach (Language::getLanguages(false) as $lang) {
            $tab->name[$lang['id_lang']] = 'Conținut Site';
        }
        $tab->add();

        return parent::install();
    }

    public function uninstall()
    {
        Tab::getInstanceFromClassName('AdminHbContent')->delete();
        foreach (array_keys(self::FIELDS) as $key) {
            Configuration::deleteByName($key);
        }
        return parent::uninstall();
    }

    public static function writeJson()
    {
        $map = [
            'hero_eyebrow'      => 'HB_HERO_EYEBROW',
            'hero_title'        => 'HB_HERO_TITLE',
            'hero_subtitle'     => 'HB_HERO_SUBTITLE',
            'hero_text'         => 'HB_HERO_TEXT',
            'hero_btn_catalog'  => 'HB_HERO_BTN_CATALOG',
            'hero_btn_packages' => 'HB_HERO_BTN_PACKAGES',
            'cta_title'         => 'HB_CTA_TITLE',
            'cta_text'          => 'HB_CTA_TEXT',
            'cta_btn'           => 'HB_CTA_BTN',
            'packages_label'    => 'HB_PKG_LABEL',
            'packages_text'     => 'HB_PKG_TEXT',
            'packages_btn'      => 'HB_PKG_BTN',
            'catalog_hero_title'    => 'HB_CAT_TITLE',
            'catalog_hero_subtitle' => 'HB_CAT_SUBTITLE',
            'catalog_hero_text'     => 'HB_CAT_TEXT',
        ];
        $data = [];
        foreach ($map as $jsonKey => $cfgKey) {
            $data[$jsonKey] = Configuration::get($cfgKey);
        }
        file_put_contents(
            _PS_ROOT_DIR_ . '/hb_content.json',
            json_encode($data, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT)
        );
    }
}
