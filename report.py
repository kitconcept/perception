from flask_table import Table, Col, LinkCol
from flask import Flask, Markup, request, url_for, render_template
import csv
from globals import Globals
import os
import gdrive
import csv
import collections
import utils as utils
import subprocess

app = Flask(__name__)
if request:  # Check for a request
    pass
    # report_name = request.args.get('report_name')


class PDFItem(object):
    def __init__(self, id, errors, title, description):
        self.id = id
        self.errors = errors
        self.title = title
        self.description = description
        self.report_type = ''

    @classmethod
    def get_items_unique_pdf(cls, report_type=False):
        report_name = ''
        if request:
            report_name = request.args.get('id')
        csv_path = Globals.gbl_report_folder + report_name
        if report_type == 'pdf_internal':
            csv_path = csv_path + '\\PDF\\internal_pdf_a.csv'
            # csv_path = Item.get_items_unique_pdf(csv_path)
        elif report_type == 'pdf_external':
            csv_path = csv_path + '\\PDF\\external_pdf_a.csv'
            # csv_path = Item.get_items_unique_pdf(csv_path)
        # totalpdfs = collections.Counter()
        istagged = collections.Counter()
        isform = collections.Counter()
        isencrypted = collections.Counter()
        word_count = collections.Counter()
        totalpdfs = 0
        first_row = True
        items = []
        if os.path.exists(csv_path):
            with open(csv_path, 'r', encoding="utf8") as input_file:
                for row in csv.reader(input_file, delimiter=','):
                    totalpdfs += 1
                    if first_row:
                        first_row = False
                    else:
                        try:
                            # If istagged or row[6] = False
                            # totalpdfs[row[0]] += 1
                            istagged[row[6]] += 1
                            isform[row[9]] += 1
                            isencrypted[row[4]] += 1
                            word_count[row[12]] += 1
                        except Exception as e:
                            print(e.__str__())
                        finally:
                            continue
            row_header = ['Errors', 'Title', 'Description', ]
            if csv_path.find('pdf'):
                if csv_path.find('pdf_internal'):
                    csv_path = os.path.split(csv_path)[0] + '\\PDF_REPORT_SUMMARY_INTERNAL.csv'
                elif csv_path.find('pdf_external'):
                    csv_path = os.path.split(csv_path)[0] + '\\PDF_REPORT_SUMMARY_EXTERNAL.csv'

            with open(csv_path, 'w', newline='', encoding="utf8") as output_file:
                csv_writer = csv.writer(output_file, quoting=csv.QUOTE_ALL)
                csv_writer.dialect.lineterminator.replace('\n', '')
                csv_writer.writerow(row_header)
                # for i in range(istagged.most_common().__len__()):
                if istagged.most_common().__len__() > 0:
                    error_count = 0
                    for fail in istagged.most_common():
                        if fail[0] == 'FALSE':
                            error_count += fail[1]
                        if fail[0].find(
                                'IsTagged: type object \'PDFDocument\' has no attribute \'is_extractable\'') >= 0:
                            error_count += fail[1]

                    csv_writer.writerow([error_count, 'Untagged PDFs', 'Untagged PDFs ...'])
                # for i in range(isform.most_common().__len__()):
                if isform.most_common().__len__() > 0:
                    error_count = 0
                    for fail in isform.most_common():
                        if fail[0] != 'FALSE':
                            if not fail[0].find('FORMS: getFields() missing') >= 0:
                                if not fail[0].find('FORMS: file has not been decrypted') >= 0:
                                    error_count += fail[1]
                    csv_writer.writerow([error_count, 'Form elements found.', 'Forms in PDFs ...'])
                # for i in range(isencrypted.most_common().__len__()):
                if isencrypted.most_common().__len__() > 0:
                    error_count = 0
                    for fail in isencrypted.most_common():
                        if fail[0] != 'FALSE':
                            error_count += fail[1]
                    csv_writer.writerow([error_count, 'Failed or Encrypted PDFs', 'Encrypted PDFs are ...'])
                output_file.close()
                try:
                    gdrive_items = []
                    i = 0
                    with open(csv_path, 'r', encoding="utf8") as f:
                        csv_file = csv.reader(f)
                        for row in csv_file:
                            if i == 0:
                                gdrive_items.append(PDFItem(i, row[0], row[1], row[2]))
                                i += 1
                                continue
                            else:
                                print(row)
                                # if not row[2] in items[i].description:
                                items.append(PDFItem(i, row[0] + ' out of ' + totalpdfs.__str__() +
                                                     ' scanned.', row[1], row[2]))
                                gdrive_items.append(PDFItem(i, row[0], row[1], row[2]))
                                i += 1
                    f.close()
                except Exception as e:
                    msg = e.__str__() + ' get_items:01'
                    print(msg)
                    # utils.logline(self.log + '_axe_log.txt', msg)
                output_file.close()
                gdrive.GDRIVE(report_name, report_type, gdrive_items)
        else:
            items.append(PDFItem('No PDFs were discovered or scanned.', '', '', ''))

        return items

    @classmethod
    def get_sorted_by(cls, sort, report_type=False, reverse=False):
        return sorted(
            cls.get_items_unique_pdf(report_type),
            key=lambda x: getattr(x, sort),
            reverse=reverse)


class PDFTable(Table):
    # Define table columns
    # id = Col('id')
    errors = Col('Number of Errors')
    title = Col('Error Type')
    description = Col('Error Description')
    allow_sort = True

    # Column key sort
    def sort_url(self, col_key, reverse=False):
        if reverse:
            direction = 'desc'
        else:
            direction = 'asc'
        return url_for('index', sort=col_key, direction=direction)


class CommanderItem(object):
    def __init__(self, id, report, address, spider, axe, lighthouse, pdf_internal, pdf_external):
        self.id = id
        self.report = report
        self.address = address
        self.spider = spider
        self.axe = axe
        self.lighthouse = lighthouse
        self.pdf_internal = pdf_internal
        self.pdf_external = pdf_external

    @classmethod
    def get_sorted_by(cls, id, sort, report_type=False, reverse=False):
        return sorted(
            cls.get_reports_list(),
            key=lambda x: getattr(x, sort),
            reverse=reverse)

    @classmethod
    def get_reports_list(cls):
        items = []
        i = 1
        for row in os.listdir(Globals.gbl_report_folder):
            seo_complete = 'No progress data available.'
            axe_complete = 'No progress data available.'
            lighthouse_complete = 'No progress data available.'
            pdf_internal_complete = 'No progress data available.'
            pdf_external_complete = 'No progress data available.'
            logs = Globals.gbl_report_folder + row + '\\logs\\'

            if os.path.exists(Globals.gbl_report_folder + row + '\\SPIDER_' + row + '\\crawl.seospider'):
                seo_complete = '100%'
            elif os.path.exists(logs + '_spider_progress_log.txt'):
                with open(logs + '_spider_progress_log.txt', 'r') as f:
                    lines = f.read().splitlines()
                    seo_complete = lines[-1]
            if os.path.exists(logs + '_axe_chrome_log.txt'):
                with open(logs + '_axe_chrome_log.txt', 'r') as f:
                    lines = f.read().splitlines()
                    for line in reversed(lines):
                        if line.find('>>> Remaining URLs for [AXE]: ') > 0:
                            axe_complete = line[31:line.rfind('2020')]
                            break
            if os.path.exists(logs + '_lighthouse_progress_log.txt'):
                with open(logs + '_lighthouse_progress_log.txt', 'r') as f:
                    lines = f.read().splitlines()
                    for line in reversed(lines):
                        if line.find('>>> Remaining URLs for [Lighthouse]: ') > 0:
                            lighthouse_complete = line[38:line.rfind('2020')]
                            break
            if os.path.exists(logs + '_pdf_internal_log.txt'):
                with open(logs + '_pdf_internal_log.txt', 'r') as f:
                    lines = f.read().splitlines()
                    for line in reversed(lines):
                        if line.find('>>> Remaining PDFs:') > 0:
                            pdf_internal_complete = line[21:line.rfind('2020')]
                            break
            if os.path.exists(logs + '_pdf_external_log.txt'):
                with open(logs + '_pdf_external_log.txt', 'r') as f:
                    lines = f.read().splitlines()
                    for line in reversed(lines):
                        if line.find('>>> Remaining PDFs:') > 0:
                            pdf_external_complete = line[21:line.rfind('2020')]
                            break
            items.append(CommanderItem(i, row, 'http://a11y-perception.ddns.net/report?report_name=' + row,
                                       seo_complete, axe_complete, lighthouse_complete,
                                       pdf_internal_complete, pdf_external_complete))
            i += 1
        return items


class CommanderTable(Table):
    # Define table columns
    # id = Col('id')
    report = Col('Report Name')
    # address = Col('Report Address')
    address = LinkCol('Report Address', 'reports', url_kwargs=dict(id='report'), attr='report', allow_sort=False)
    spider = Col('Spider Progress (complete)')
    spider_rs = LinkCol('RESTART CRAWL', 'action_restart',
                        url_kwargs=dict(id='report'), url_kwargs_extra=dict(report_type='spider'))
    axe = Col('AXE Progress (remaining)')
    axe_rs = LinkCol('RESTART AXE', 'action_restart',
                     url_kwargs=dict(id='report'), url_kwargs_extra=dict(report_type='axe'))
    lighthouse = Col('Lighthouse Progress (remaining)')
    lighthouse_rs = LinkCol('RESTART Lighthouse', 'action_restart',
                            url_kwargs=dict(id='report'), url_kwargs_extra=dict(report_type='lighthouse'))
    pdf_internal = Col('PDF Internal Progress (remaining)')
    pdf_internal_rs = LinkCol('RESTART INTERNAL PDF', 'action_restart',
                              url_kwargs=dict(id='report'), url_kwargs_extra=dict(report_type='pdf_internal'))
    pdf_external = Col('PDF External Progress (remaining)')
    pdf_external_rs = LinkCol('RESTART EXTERNAL PDF', 'action_restart',
                              url_kwargs=dict(id='report'), url_kwargs_extra=dict(report_type='pdf_external'))
    allow_sort = True

    # Column key sort
    def sort_url(self, col_key, reverse=False):
        if reverse:
            direction = 'desc'
        else:
            direction = 'asc'
        return url_for('index', sort=col_key, direction=direction)


class Item(object):
    def __init__(self, id, test, url, error_count, error, error_description):
        self.id = id
        self.test = test
        self.url = url
        self.error_count = error_count
        self.error = error
        self.error_description = error_description

    @classmethod
    def get_items(cls, report_type=False):
        i = 0
        i += 1
        items = []
        report_name = ''
        if request:
            report_name = request.args.get('id')
        csv_path = Globals.gbl_report_folder + report_name
        if report_type == 'lighthouse':
            csv_path = csv_path + ('\\LIGHTHOUSE\\LIGHTHOUSE_REPORT.csv')
            csv_path = Item.get_items_unique(csv_path, report_type)
        if report_type == 'axe_c_summary':
            csv_path = csv_path + ('\\AXE\\Chrome\\AXEChrome_REPORT.csv')
            csv_path = Item.get_items_unique(csv_path, report_type)
        if report_type == 'axe_c':
            csv_path = csv_path + ('\\AXE\\Chrome\\AXEChrome_REPORT.csv')
            # csv_path = Item.get_items(csv_path, report_type)

        gdrive_items = []
        items = []
        i = 0
        try:
            with open(csv_path, encoding="utf8") as f:
                csv_file = csv.reader(f)
                for row in csv_file:
                    if i == 0:
                        gdrive_items.append(Item(i, row[0].upper(), row[1].upper(), row[2].upper(),
                                                 row[3].upper(), row[4].upper()))
                        i += 1
                        continue
                    else:
                        print(row)
                        IL = Item(i, row[0], row[1], row[2], row[3], row[4])
                        items.append(IL)
                        gdrive_items.append(IL)
                        i += 1
            f.close()
        except Exception as e:
            msg = e.__str__() + ' get_items:01'
            print(msg)
            # utils.logline(self.log + '_axe_log.txt', msg)
        gdrive.GDRIVE(report_name, report_type, gdrive_items)
        return items

    @classmethod
    def get_sorted_by(cls, sort, report_type=False, reverse=False):
        return sorted(
            cls.get_items(report_type),
            key=lambda x: getattr(x, sort),
            reverse=reverse)

    @classmethod
    def get_items_by_id(cls, id):
        return [i for i in cls.get_items() if i.id == id][0]

    @classmethod
    def get_items_unique(cls, csv_path, report_type):
        title = collections.Counter()
        description = collections.Counter()
        first_row = True
        if os.path.exists(csv_path):
            with open(csv_path, 'r', encoding="utf8") as input_file:
                for row in csv.reader(input_file, delimiter=','):
                    if first_row:
                        first_row = False
                        continue
                    else:
                        try:
                            if report_type == 'lighthouse':
                                title[row[3]] += 1
                                description[row[4]] += 1
                            if report_type == 'axe_c':
                                title[row[4]] += 1
                                description[row[4]] += 1
                            if report_type == 'axe_c_summary':
                                title[row[4]] += 1
                                description[row[5]] += 1
                        except Exception as e:
                            print(e.__str__())
                        finally:
                            continue

            row_header = ['Test', 'URL', 'Error Count', 'Error', 'Error Description']
            if report_type == 'axe_c_summary':
                csv_path = csv_path.replace('AXEChrome_REPORT.csv', 'AXEChrome_REPORT_SUMMARY.csv')
            if report_type == 'lighthouse':
                csv_path = csv_path.replace('LIGHTHOUSE_REPORT.csv', 'LIGHTHOUSE_REPORT_SUMMARY.csv')
            if os.path.exists(csv_path):
                os.remove(csv_path)
            # Write summary report
            with open(csv_path, 'a+', newline='', encoding="utf8") as output_file:
                csv_writer = csv.writer(output_file, quoting=csv.QUOTE_ALL)
                csv_writer.dialect.lineterminator.replace('\n', '')
                csv_writer.writerow(row_header)
                for i in range(title.most_common().__len__()):
                    try:
                        csv_writer.writerow([report_type, 'url', title.most_common()[i][1], title.most_common()[i][0],
                                             description.most_common()[i][0]])
                    except Exception as e:
                        msg = e.__str__() + ' get_unique:02'
                        print(msg)
                        # utils.logline(self.log + '_lighthouse_log.txt', msg)
            output_file.close()
        return csv_path


class Table(Table):
    # Define table columns
    error_count = Col('Error Count')
    error = Col('Error')
    error_description = Col('Error Description')
    allow_sort = True

    # TODO: Column key sort
    def sort_url(self, col_key, reverse=False):
        if reverse:
            direction = 'desc'
        else:
            direction = 'asc'
        return url_for('index', sort=col_key, direction=direction)


class DashItem(object):
    def __init__(self, id, summary, url_count, percentage, urls_total, description):
        self.id = id
        self.metric = summary
        self.url_count = url_count
        self.percentage = percentage
        self.urls_total = urls_total
        self.description = description

    @classmethod
    def get_items(cls, report_type=False):
        i = 0
        i += 1
        items = []
        report_name = ''
        if request:
            report_name = request.args.get('id')
        csv_path = Globals.gbl_report_folder + report_name + '\\SPIDER\\crawl_overview.csv'
        gdrive_items = []
        items = []
        i = 0
        try:
            # Write the dash
            with open(csv_path, encoding="utf8") as f:
                csv_file = csv.reader(f)
                for row in csv_file:
                    line = csv_file.line_num
                    if line == 1:
                        gdrive_items.append(DashItem(line, row[0], row[1], '', '', ''))
                    elif line == 2:
                        gdrive_items.append(DashItem(line, row[0], row[1], '', '', ''))
                    elif line == 3:
                        gdrive_items.append(DashItem(line, row[0], row[1], '', '', ''))
                    elif line == 5:
                        gdrive_items.append(DashItem(line, 'Summary', 'Number of URLs', '% of Total URLs',
                                                     'Total URLs', 'Total URLs Description'))
                    elif line == 6 or line == 7 or line == 9 or line == 12 or line == 13:
                        gdrive_items.append(DashItem(line, row[0], row[1], row[2], row[3], row[4]))
                    elif line == 16 or line == 21:
                        gdrive_items.append(DashItem(line, 'Internal ' + row[0], row[1], row[2], row[3], row[4]))
                    elif line == 28 or line == 32:
                        gdrive_items.append(DashItem(line, 'External ' + row[0], row[1], row[2], row[3], row[4]))
                    elif line == 44 or line == 45 or line == 46 or line == 51 or line == 52:
                        gdrive_items.append(DashItem(line, 'Response Codes: ' + row[0], row[1], row[2], row[3], row[4]))
                    elif line == 55:
                        gdrive_items.append(DashItem(line, 'Content: ' + row[0], row[1], row[2], row[3], row[4]))
                    elif line == 60:
                        gdrive_items.append(DashItem(line, 'URL: ' + row[0], row[1], row[2], row[3], row[4]))
                    elif line == 69 or line == 70:
                        gdrive_items.append(DashItem(line, 'Page Titles: ' + row[0], row[1], row[2], row[3], row[4]))
                    elif line == 80 or line == 81:
                        gdrive_items.append(DashItem(line, 'Meta Description: ' + row[0], row[1], row[2], row[3], row[4]))
                    elif line == 89 or line == 90:
                        gdrive_items.append(DashItem(line, 'Meta Keywords: ' + row[0], row[1], row[2], row[3], row[4]))
                    elif line == 96 or line == 97:
                        gdrive_items.append(DashItem(line, 'H1: ' + row[0], row[1], row[2], row[3], row[4]))
                    elif line == 103 or line == 104:
                        gdrive_items.append(DashItem(line, 'H2: ' + row[0], row[1], row[2], row[3], row[4]))
                    elif line == 110 or line == 111 or line == 112:
                        gdrive_items.append(DashItem(line, 'Images: ' + row[0], row[1], row[2], row[3], row[4]))
            f.close()
        except Exception as e:
            msg = e.__str__() + ' get_items:01'
            print(msg)
            # utils.logline(self.log + '_axe_log.txt', msg)
        gdrive.GDRIVE(report_name, report_type, gdrive_items)
        return items

    @classmethod
    def get_sorted_by(cls, sort, report_type=False, reverse=False):
        return sorted(
            cls.get_items(report_type),
            key=lambda x: getattr(x, sort),
            reverse=reverse)

    @classmethod
    def get_items_by_id(cls, id):
        return [i for i in cls.get_items() if i.id == id][0]

    @classmethod
    def get_items_unique(cls, csv_path, report_type):
        title = collections.Counter()
        description = collections.Counter()
        first_row = True
        if os.path.exists(csv_path):
            with open(csv_path, 'r', encoding="utf8") as input_file:
                for row in csv.reader(input_file, delimiter=','):
                    if first_row:
                        first_row = False
                        continue
                    else:
                        try:
                            if report_type == 'lighthouse':
                                title[row[3]] += 1
                                description[row[4]] += 1
                            if report_type == 'axe':
                                title[row[4]] += 1
                                description[row[4]] += 1
                            if report_type == 'axe_u':
                                title[row[4]] += 1
                                description[row[5]] += 1
                        except Exception as e:
                            print(e.__str__())
                        finally:
                            continue

            row_header = ['Test', 'URL', 'Error Count', 'Error', 'Error Description']
            if report_type == 'axe' or 'axe_u':
                csv_path = csv_path.replace('AXE_REPORT.csv', 'AXE_REPORT_SUMMARY.csv')
            if report_type == 'lighthouse':
                csv_path = csv_path.replace('LIGHTHOUSE_REPORT.csv', 'LIGHTHOUSE_REPORT_SUMMARY.csv')
            if os.path.exists(csv_path):
                os.remove(csv_path)
            # Write summary report
            with open(csv_path, 'a+', newline='', encoding="utf8") as output_file:
                csv_writer = csv.writer(output_file, quoting=csv.QUOTE_ALL)
                csv_writer.dialect.lineterminator.replace('\n', '')
                csv_writer.writerow(row_header)
                for i in range(title.most_common().__len__()):
                    try:
                        csv_writer.writerow([report_type, 'url', title.most_common()[i][1], title.most_common()[i][0],
                                             description.most_common()[i][0]])
                    except Exception as e:
                        msg = e.__str__() + ' get_unique:02'
                        print(msg)
                        # utils.logline(self.log + '_lighthouse_log.txt', msg)
            output_file.close()
        return csv_path


class DashTable(Table):
    # Define table columns
    error_count = Col('Error Count')
    error = Col('Error')
    error_description = Col('Error Description')
    allow_sort = True

    # TODO: Column key sort
    def sort_url(self, col_key, reverse=False):
        if reverse:
            direction = 'desc'
        else:
            direction = 'asc'
        return url_for('index', sort=col_key, direction=direction)
